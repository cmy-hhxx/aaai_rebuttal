"""Offline mocks for v2 pilot execution policy; makes no network requests."""
import importlib.util
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("v2_pilot_evaluation", Path(__file__).with_name("evaluate_pilot.py"))
assert spec is not None and spec.loader is not None
pilot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pilot)


def response(value):
    return {"choices": [{"message": {"content": json.dumps(value)}}]}


def judged():
    return {"verdict": "valid", "reason": "A checkable deduction.", "error_types": [], "depth_score": 1,
            "depth_evidence": "One implication.", "reasoning_type_tags": ["deduction"],
            "constraint_type_tags": ["ordering"], "scenario": "abstract", "explanation_score": 4,
            "explanation_evidence": "The stated order determines the answer.", "solver_correct": [True]}


class WrapperChecks(unittest.TestCase):
    def fixture(self, folder):
        here = Path(folder)
        (here / "audit").mkdir()
        items = [{"anon_id": f"{i:020x}", "problem": "A precedes B. Which is first?" if i < 3 else "",
                  "answer": "A", "explanation": "NATIVE_EXPLANATION_MUST_NOT_BE_SENT"} for i in range(84)]
        keys = [{"anon_id": item["anon_id"], "method": ("puzzleforge", "direct", "framework")[i//28],
                 "seed_id": f"seed_{i%28//2}"} for i, item in enumerate(items)]
        for name, values in (("audit_blind.jsonl", items), ("audit_key.jsonl", keys)):
            (here / "audit" / name).write_text("".join(json.dumps(value) + "\n" for value in values))
        return here

    def test_truncation_and_exhausted_schema_are_local_unknown_without_fake_judgment(self):
        owner = self
        class FakeClient:
            calls = []
            lock = threading.Lock()
            def __init__(self, *args, **kwargs):
                owner.assertEqual(kwargs["max_calls"], 400)
                owner.assertEqual(kwargs["timeout"], 300)
            def complete(self, messages, tag):
                with self.lock:
                    self.calls.append(tag)
                owner.assertNotIn("NATIVE_EXPLANATION_MUST_NOT_BE_SENT", json.dumps(messages))
                anon = tag.split(":")[1]
                if anon == "0".zfill(20):
                    raise pilot.APIError("truncated_response")
                if ":solve:" in tag:
                    owner.assertNotIn('"canonical_answer"', json.dumps(messages))
                    return response({"answer": "A", "certificate": "A precedes B."})
                return response({}) if anon == "1".zfill(20) else response(judged())
        with tempfile.TemporaryDirectory() as folder:
            here = self.fixture(folder)
            with patch.object(pilot, "HERE", here), patch.object(pilot, "ChatClient", FakeClient), patch.object(pilot, "_outputs"), patch("builtins.print"):
                pilot.evaluate("http://localhost/v1")
                saved = [json.loads(path.read_text()) for path in (here / "auto/items").glob("*.json")]
                self.assertEqual(len(saved), 84)
                unknown = [r for r in saved if r.get("assessment_status") == "execution_unknown"]
                self.assertEqual(len(unknown), 2)
                self.assertTrue(all(r["judges"] == [] and r["label_origin"] == "execution_policy" for r in unknown))
                self.assertEqual(sum(r["status"] == "unavailable" for r in saved), 81)
                self.assertEqual(sum(":00000000000000000000:solve:" in tag for tag in FakeClient.calls), 1)
                self.assertEqual(len(FakeClient.calls), 7)
                pilot.evaluate("http://localhost/v1")
                self.assertEqual(len(FakeClient.calls), 7)

    def test_network_http_and_budget_failures_are_not_puzzle_labels(self):
        for kind in ("transport_error", "http_error", "call_budget_exhausted"):
            class FakeClient:
                def __init__(self, *args, **kwargs):
                    pass
                def complete(self, messages, tag):
                    raise pilot.APIError(kind)
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as folder:
                here = self.fixture(folder)
                with patch.object(pilot, "HERE", here), patch.object(pilot, "ChatClient", FakeClient), patch.object(pilot, "_outputs"), patch("builtins.print"):
                    with self.assertRaises(pilot.APIError) as caught:
                        pilot.evaluate("http://localhost/v1")
                    self.assertEqual(caught.exception.kind, kind)
                saved = [json.loads(path.read_text()) for path in (here / "auto/items").glob("*.json")]
                self.assertTrue(all(row["status"] == "unavailable" for row in saved))

    def test_report_banner_never_calls_policy_unknown_a_complete_judgment(self):
        with tempfile.TemporaryDirectory() as folder:
            here = Path(folder)
            (here / "auto").mkdir()
            report = here / "auto/auto_report.md"
            report.write_text("已处理 4/4 题；有完整模型评估 3 题；无输出槽位 1；pending 0。\n\n模型共识只是代理。\n\n| 组别 | 完整评估 |\n")
            labels = [{"status":"completed", "assessment_status":"model_judgment"},
                      {"status":"completed", "assessment_status":"model_judgment"},
                      {"status":"completed", "assessment_status":"execution_unknown"}, {"status":"unavailable"}]
            with patch.object(pilot, "HERE", here):
                pilot.fix_banner(labels)
                first = report.read_text()
                pilot.fix_banner(labels)
                self.assertEqual(first, report.read_text())
            self.assertIn("真实模型判定 2 题；执行未决 1 题", first)
            self.assertIn("已处理有题(含执行未决)", first)
            self.assertNotIn("有完整模型评估", first)
            self.assertNotIn("| 完整评估 |", first)
            self.assertIn("不能称为完整模型评审", first)


if __name__ == "__main__":
    unittest.main()
