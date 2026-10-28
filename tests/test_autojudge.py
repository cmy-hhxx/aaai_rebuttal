import json
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from experiment.api import APIError
from experiment.autojudge import EvaluationError, _paired_cases, _paired_proxy, automatic_report, consensus, run_audit


def response(value):
    return {"choices": [{"message": {"content": json.dumps(value)}}]}


def judgment(count, verdict="valid"):
    return {"verdict": verdict, "reason": "Independent constraint check found no contradiction.",
            "error_types": [], "depth_score": 2 if verdict == "valid" else None,
            "depth_evidence": "A determines B; B determines the query.",
            "reasoning_type_tags": ["deduction"], "constraint_type_tags": ["ordering"],
            "scenario": "abstract", "explanation_score": 3 if verdict == "valid" else None,
            "explanation_evidence": "The two necessary implications can be checked.",
            "solver_correct": [True] * count if verdict == "valid" else [None] * count}


class AutomaticJudgeTest(unittest.TestCase):
    def items(self):
        return [{"anon_id": "a", "problem": "A precedes B. Which is first?", "answer": "SECRET_ANSWER",
                 "explanation": "NATIVE_EXPLANATION_CANARY", "method": "METHOD_CANARY",
                 "seed_id": "SEED_CANARY"}]

    def test_solver_is_answer_blind_and_key_never_transmitted(self):
        calls = []
        def fake(model, messages, tag):
            calls.append((model, messages, tag))
            prompt = json.dumps(messages)
            self.assertNotIn("NATIVE_EXPLANATION_CANARY", prompt)
            self.assertNotIn("METHOD_CANARY", prompt)
            self.assertNotIn("SEED_CANARY", prompt)
            self.assertNotIn("PRIVATE_SOURCE", prompt)
            if ":solve:" in tag:
                self.assertNotIn("SECRET_ANSWER", prompt)
                return response({"answer": "A", "certificate": "A precedes B by the stated relation."})
            user = json.loads(messages[1]["content"])
            self.assertEqual(user["canonical_answer"], "SECRET_ANSWER")
            return response(judgment(len(user["attempts"])))
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder)
            key = [{"anon_id": "a", "method": "puzzleforge", "seed_id": "PRIVATE_SOURCE"}]
            rows = run_audit(self.items(), out, "http://localhost/v1", ["m1", "m2"], key=key, k=2, request_fn=fake)
            self.assertEqual(len(calls), 6)
            self.assertEqual(consensus(rows[0]), "valid")
            self.assertTrue((out / "model_labels.jsonl").exists())
            self.assertIn("非人工复核", (out / "auto_report.md").read_text())
            self.assertFalse((out / "audit_labels.csv").exists())
            resumed = run_audit(self.items(), out, "http://localhost/v1", ["m1", "m2"], key=key, k=2,
                                request_fn=lambda *args: self.fail("Resume made an API request"))
            self.assertEqual(rows, resumed)

    def test_empty_slot_costs_no_api_and_duplicate_models_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder)
            rows = run_audit([{"anon_id": "empty", "problem": "", "answer": None}], out,
                             "http://localhost", ["m"], request_fn=lambda *args: self.fail("Unexpected request"))
            self.assertEqual(consensus(rows[0]), "unavailable")
            self.assertIn("仅单模型初评", (out / "auto_report.md").read_text())
            with self.assertRaises(ValueError):
                run_audit([], out, "http://localhost", ["m", "m"])

    def test_disagreement_is_uncertain_and_difficulty_na(self):
        row = {"anon_id": "a", "status": "completed", "k": 1,
               "attempts": [{"panel": 0}, {"panel": 1}],
               "judges": [judgment(2), judgment(2, "invalid")]}
        self.assertEqual(consensus(row), "uncertain")
        report = automatic_report([row], ["m1", "m2"])
        self.assertIn("avg@k=NA", report)
        self.assertIn("| overall | 1 | 1 | 0 | 0 | 0/1 (0.000) | 1/1 (1.000)", report)

    def test_format_or_api_error_does_not_become_bad_puzzle(self):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder)
            with self.assertRaises(APIError):
                run_audit(self.items(), out, "http://localhost", ["m"],
                          request_fn=lambda *args: (_ for _ in ()).throw(APIError("call_budget_exhausted")))
            self.assertFalse((out / "model_labels.jsonl").exists())
            rows = run_audit(self.items(), out, "http://localhost", ["m"],
                             request_fn=lambda *args: response({"answer": "x"}))
            self.assertEqual([row["status"] for row in rows], ["execution_unknown"] * len(rows))
            labels = [json.loads(line) for line in (out / "model_labels.jsonl").read_text().splitlines() if line]
            self.assertTrue(labels and all(label["judges"] == [] for label in labels))

    def test_malformed_solver_and_judge_outputs_recover_with_fixed_tags(self):
        calls = []
        original_inputs = {}
        def fake(model, messages, tag):
            calls.append(tag)
            task = "solve" if ":solve:" in tag else "judge"
            original_inputs.setdefault(task, messages[1])
            self.assertEqual(messages[1], original_inputs[task])
            if tag.endswith("format-attempt-0"):
                if task == "solve":
                    return {"choices": [{"message": {"content": "not JSON"}}]}
                return response({"verdict": "valid"})
            self.assertTrue(tag.endswith("format-attempt-1"))
            self.assertIn("failed required JSON/schema validation", messages[-1]["content"])
            return response({"answer": "A", "certificate": "A is first by the stated ordering."}) if task == "solve" else response(judgment(1))
        with tempfile.TemporaryDirectory() as folder:
            rows = run_audit(self.items(), Path(folder), "http://localhost", ["m"], k=1, request_fn=fake)
            self.assertEqual(consensus(rows[0]), "valid")
            self.assertEqual(len(calls), 4)
            self.assertEqual(len(set(calls)), 4)

    def test_schema_retry_resume_replays_cache_and_obeys_shared_budget(self):
        class FakeClient:
            cache = {}
            paid_calls = 0
            interrupted = False
            def __init__(self, *args, **kwargs):
                self.max_calls = kwargs["max_calls"]
            def complete(self, messages, tag):
                identity = (tag, json.dumps(messages, sort_keys=True))
                if identity in self.cache:
                    return self.cache[identity]
                if type(self).paid_calls >= self.max_calls:
                    raise APIError("call_budget_exhausted")
                type(self).paid_calls += 1
                if ":judge:" in tag and not type(self).interrupted:
                    type(self).interrupted = True
                    raise APIError("transport_error")
                if ":solve:" in tag:
                    value = response({"answer": "A"}) if tag.endswith("format-attempt-0") else response({"answer": "A", "certificate": "Check"})
                else:
                    value = response(judgment(1))
                self.cache[identity] = value
                return value
        with tempfile.TemporaryDirectory() as folder, patch("experiment.autojudge.ChatClient", FakeClient):
            out = Path(folder)
            with self.assertRaises(APIError):
                run_audit(self.items(), out, "http://localhost", ["m"], k=1, max_calls=4)
            self.assertEqual(FakeClient.paid_calls, 3)
            rows = run_audit(self.items(), out, "http://localhost", ["m"], k=1, max_calls=4)
            self.assertEqual(consensus(rows[0]), "valid")
            self.assertEqual(FakeClient.paid_calls, 4)
            self.assertEqual(len(FakeClient.cache), 3)  # Bad solver, repaired solver, valid judge.
            run_audit(self.items(), out, "http://localhost", ["m"], k=1, max_calls=4)
            self.assertEqual(FakeClient.paid_calls, 4)

    def test_schema_retry_exhaustion_is_bounded_and_creates_no_label(self):
        tags = []
        def fake(model, messages, tag):
            tags.append(tag)
            return response({"answer": "A"})
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder)
            rows = run_audit(self.items(), out, "http://localhost", ["m"], k=1, request_fn=fake)
            self.assertEqual(len(tags), 3)
            self.assertEqual([tag.rsplit(":", 1)[1] for tag in tags],
                             ["format-attempt-0", "format-attempt-1", "format-attempt-2"])
            # Exhausted schema repair is execution-unknown, never a fabricated label.
            self.assertEqual(rows[0]["status"], "execution_unknown")
            self.assertEqual(rows[0]["judges"], [])
            self.assertEqual(consensus(rows[0]), "uncertain")
            labels = [json.loads(line) for line in (out / "model_labels.jsonl").read_text().splitlines() if line]
            self.assertTrue(labels and all(label["judges"] == [] for label in labels))

    def test_shared_cap_is_passed_to_fresh_client_every_request(self):
        class FakeClient:
            constructed = []
            def __init__(self, *args, **kwargs):
                self.constructed.append((args[2], kwargs["max_calls"]))
            def complete(self, messages, tag):
                return response({"answer": "A", "certificate": "Check"}) if ":solve:" in tag else response(judgment(2))
        with tempfile.TemporaryDirectory() as folder, patch("experiment.autojudge.ChatClient", FakeClient):
            run_audit(self.items(), Path(folder), "http://localhost", ["m1", "m2"], k=1, max_calls=4)
            self.assertEqual(len(FakeClient.constructed), 4)
            self.assertEqual(len({str(cache) for cache, _ in FakeClient.constructed}), 1)
            self.assertEqual({cap for _, cap in FakeClient.constructed}, {4})

    def test_resume_rejects_changed_input_or_decoding(self):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder)
            run_audit([], out, "http://localhost", ["m"])
            with self.assertRaises(ValueError):
                run_audit([], out, "http://localhost", ["m"], parameters={"temperature": 1})

    def test_paired_cases_keep_support_refute_and_similar(self):
        rows, key = [], []
        for seed in ("support", "refute", "same"):
            for method in ("puzzleforge", "direct"):
                for slot in range(2):
                    anon = f"{seed}-{method}-{slot}"
                    valid = seed == "same" or (seed == "support" and method == "puzzleforge") or (seed == "refute" and method == "direct")
                    rows.append({"anon_id": anon, "status": "completed", "judges": [judgment(1, "valid" if valid else "invalid")]})
                    key.append({"anon_id": anon, "method": method, "seed_id": seed})
        self.assertEqual({case["direction"] for case in _paired_cases(rows, key)}, {"supporting", "refuting", "similar"})

    def test_unavailable_denominator_and_pending_are_not_dropped(self):
        valid = {"anon_id": "valid", "status": "completed", "k": 1, "attempts": [{"panel": 0}], "judges": [judgment(1)]}
        failed = {"anon_id": "failed", "status": "unavailable", "judges": []}
        key = [{"anon_id": anon, "method": "direct", "seed_id": "s"} for anon in ("valid", "failed", "pending")]
        partial = automatic_report([valid, failed], ["m"], key)
        self.assertIn("待处理pending 1", partial)
        self.assertIn("| direct | 3 | 1 | 1 | 1 | NA | NA", partial)
        full = automatic_report([valid, failed], ["m"], key[:2])
        self.assertIn("| direct | 2 | 1 | 1 | 0 | 1/2 (0.500) | 1/2 (0.500)", full)

    def test_scores_aggregate_per_item_before_group_mean(self):
        first_judges = [judgment(1), judgment(1)]
        first_judges[0]["depth_score"] = 4
        first_judges[1]["depth_score"] = 2
        second_judges = [judgment(1)]
        second_judges[0]["depth_score"] = 1
        rows = [{"anon_id": anon, "status": "completed", "k": 1, "attempts": [{"panel": 0}], "judges": judges}
                for anon, judges in (("a", first_judges), ("b", second_judges))]
        report = automatic_report(rows, ["m"])
        self.assertIn("2.000 (2题)", report)  # (mean(4,2) + 1) / 2, not mean(4,2,1).

    def test_seed_pairing_includes_failures_and_distinguishes_uncertainty_bounds(self):
        rows, key = [], []
        for seed in ("s1", "s2"):
            for method in ("puzzleforge", "direct"):
                for slot in range(2):
                    anon = f"{seed}-{method}-{slot}"
                    verdict = "valid" if slot == 0 else "uncertain"
                    row = {"anon_id": anon, "status": "completed", "k": 1,
                           "attempts": [{"panel": 0}], "judges": [judgment(1, verdict)]}
                    if method == "direct" and slot == 1:
                        row = {"anon_id": anon, "status": "unavailable", "judges": []}
                    rows.append(row)
                    key.append({"anon_id": anon, "method": method, "seed_id": seed})
        result = _paired_proxy(rows, key)[0]
        self.assertEqual((result["n"], result["eligible"]), (2, 2))
        self.assertEqual(result["metrics"]["lower_minus_lower"], (0.0, 0.0, 0.0))
        self.assertEqual(result["metrics"]["upper_minus_upper"], (0.5, 0.5, 0.5))
        self.assertEqual(result["metrics"]["difference_lower"][0], 0.0)
        self.assertEqual(result["metrics"]["difference_upper"][0], 0.5)
        report = automatic_report(rows, ["m"], key)
        self.assertIn("| PF − direct | upper_minus_upper | 2/2 | +0.500", report)
        self.assertIn("点估计范围为[+0.000, +0.500]", report)
        self.assertIn("不能推断人审真值、全部质量维度", report)

    def test_parallel_items_overlap_and_export_in_stable_input_order(self):
        barrier = threading.Barrier(2)
        active, peak = 0, 0
        lock = threading.Lock()
        def fake(model, messages, tag):
            nonlocal active, peak
            if ":solve:" in tag:
                with lock:
                    active += 1
                    peak = max(peak, active)
                barrier.wait(timeout=3)
                if ":a:" in tag:
                    time.sleep(.02)
                with lock:
                    active -= 1
                return response({"answer": "A", "certificate": "By the given order."})
            return response(judgment(1))
        items = [{"anon_id": anon, "problem": "A precedes B. First?", "answer": "A"} for anon in ("a", "b")]
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder)
            rows = run_audit(items, out, "http://localhost", ["m"], k=1, workers=2, request_fn=fake)
            self.assertEqual(peak, 2)
            self.assertEqual([r["anon_id"] for r in rows], ["a", "b"])
            saved = [json.loads(line) for line in (out / "model_labels.jsonl").read_text().splitlines()]
            self.assertEqual([r["anon_id"] for r in saved], ["a", "b"])
            run_audit(items, out, "http://localhost", ["m"], k=1, workers=2,
                      request_fn=lambda *args: self.fail("Cached item requested API"))

    def test_parallel_shared_client_cap_and_partial_results_survive_failure(self):
        class BudgetClient:
            instances, calls = 0, 0
            lock = threading.Lock()
            def __init__(self, *args, **kwargs):
                self.cap = kwargs["max_calls"]
                type(self).instances += 1
            def complete(self, messages, tag):
                with self.lock:
                    if type(self).calls >= self.cap:
                        raise APIError("call_budget_exhausted")
                    type(self).calls += 1
                return response({"answer": "A", "certificate": "Check"}) if ":solve:" in tag else response(judgment(1))
        items = [{"anon_id": str(i), "problem": "A precedes B. First?", "answer": "A"} for i in range(6)]
        with tempfile.TemporaryDirectory() as folder, patch("experiment.autojudge.ChatClient", BudgetClient):
            out = Path(folder)
            with self.assertRaises(APIError):
                run_audit(items, out, "http://localhost", ["m"], k=1, workers=2, max_calls=3)
            self.assertEqual(BudgetClient.instances, 1)
            self.assertEqual(BudgetClient.calls, 3)
            self.assertTrue((out / "model_labels.jsonl").exists())
            labels = [json.loads(line) for line in (out / "model_labels.jsonl").read_text().splitlines()]
            self.assertTrue(all(row["status"] == "completed" for row in labels))
            self.assertLess(len(labels), len(items))
            self.assertIn("pending", (out / "auto_report.md").read_text())

    def test_parallel_multiple_models_are_explicitly_rejected(self):
        with tempfile.TemporaryDirectory() as folder, self.assertRaisesRegex(ValueError, "one model"):
            run_audit([], Path(folder), "http://localhost", ["m1", "m2"], workers=2)


if __name__ == "__main__":
    unittest.main()
