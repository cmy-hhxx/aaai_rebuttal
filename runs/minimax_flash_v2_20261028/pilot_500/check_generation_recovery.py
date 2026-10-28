"""Offline integration tests for the run-local recovery adapter; never call APIs."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from recover_generation import RecoveryClient, bindings, digest, pending_seeds, run, ROOT
from experiment.api import APIError, ChatClient


class RecoveryTests(unittest.TestCase):
    def test_missing_final_replays_unchanged_then_uses_remaining_attempts(self):
        for method in ("direct", "framework"):
            with self.subTest(method=method), tempfile.TemporaryDirectory() as temp:
                folder = Path(temp)
                c = json.loads((ROOT / "configs/minimax_flash_20261028.json").read_text())
                c.update(prompt_variant="paper_v2", prompt_language="zh", output_language="zh", workers=1, max_calls=200)
                source = {"id": "logic_11", "question": "A general puzzle fixture.", "answer": {"a": [1, 2]}}
                run.write_json(folder / "seeds.json", [source])
                prompt = run.prompt_paths(c, method)[0]
                relative = str(prompt.relative_to(ROOT))
                system = prompt.read_text()
                frozen = folder / "snapshot" / relative
                frozen.parent.mkdir(parents=True)
                frozen.write_text(system)
                manifest = {"config": c, "matched_slots": {"logic_11": list(range(16))},
                            "input_hashes": {relative: hashlib.sha256(system.encode()).hexdigest()}}
                cache = folder / "api_cache"
                cache.mkdir()
                (cache / "requests.jsonl").write_text(' {"event":"request_start"}\n' * 64)
                client = RecoveryClient(c["endpoint"], c["model"], cache, parameters=c["parameters"], timeout=900, retries=0, max_calls=200)
                request = {"count": 5, "already_generated_problems": [], "output_language": "zh"} if method == "direct" else {"available_libraries": c["runtime_libraries"], "target_count": 20, "output_language": "zh"}
                messages = [{"role": "system", "content": system},
                            {"role": "user", "content": json.dumps({"seed_question": source["question"], "seed_answer": source["answer"]}, ensure_ascii=False)},
                            {"role": "user", "content": json.dumps(request, ensure_ascii=False)}]
                tag = f"{method}/logic_11/0/attempt-0"
                identity = {"version": 1, "endpoint": client.endpoint, "payload": {**c["parameters"], "model": c["model"], "messages": messages, "stream": False}, "tag": tag}
                raw = {"model": c["model"], "choices": [{"finish_reason": "length", "message": {"role": "assistant", "reasoning_content": "NEVER_USE_THIS_AS_FINAL_CODE"}}], "usage": {"completion_tokens": 32768}}
                key = digest(identity)
                failure = cache / f"{key}.failure-64.json"
                run.write_json(cache / f"{key}.request.json", identity)
                run.write_json(failure, {**identity, "kind": "truncated_response", "response": raw})
                before = failure.read_bytes()
                paid_tags = []

                def fake_http(self, actual, actual_digest):
                    self._reserve_call(actual_digest, actual["tag"], 1)
                    paid_tags.append(actual["tag"])
                    count = json.loads(actual["payload"]["messages"][-1]["content"]).get("count", 0) if actual["tag"].endswith("attempt-0") else 5
                    rows = [{"problem": f"fixture {actual['tag']}/{i}", "answer": i, "explanation": "fixture"} for i in range(count)]
                    return {"model": c["model"], "choices": [{"finish_reason": "stop", "message": {"content": json.dumps(rows) if method == "direct" else "# fixture, never executed"}}]}

                def fake_executor(code, seed, count, work_dir, **kwargs):
                    return [{"problem": f"fixture {seed}/{i}", "answer": i, "explanation": "fixture"} for i in range(count)]

                with patch.object(ChatClient, "_complete", fake_http), patch.object(run, "run_generator", fake_executor), patch("urllib.request.build_opener", side_effect=AssertionError("No network in offline tests")), bindings(client):
                    run.generate(manifest, folder, method)
                self.assertNotIn(tag, paid_tags)
                self.assertEqual(client._calls, 64 + len(paid_tags))
                self.assertEqual(failure.read_bytes(), before)
                self.assertEqual(read_json(failure)["response"], raw)
                repair = read_json(folder / "traces" / method / "logic_11" / "0" / "attempt-1.json")
                self.assertEqual(repair[-2], {"role": "assistant", "content": ""})
                self.assertIn("truncated at unchanged 32768", repair[-1]["content"])
                self.assertNotIn("NEVER_USE_THIS_AS_FINAL_CODE", json.dumps(repair))
                self.assertEqual(read_json(folder / "results" / method / "logic_11" / "00.json")[0]["attempts"], 2)

    def test_identity_mismatch_never_resamples(self):
        with tempfile.TemporaryDirectory() as temp:
            client = RecoveryClient("https://example.com/v1", "fixture", Path(temp), parameters={"max_completion_tokens": 32768})
            messages = [{"role": "user", "content": "fixture"}]
            identity = {"version": 1, "endpoint": client.endpoint, "payload": {"max_completion_tokens": 32768, "model": "fixture", "messages": messages, "stream": False}, "tag": "framework/s/0/attempt-0"}
            key = digest(identity)
            run.write_json(Path(temp) / f"{key}.failure-1.json", {**identity, "tag": "different", "kind": "truncated_response"})
            with patch.object(ChatClient, "_complete", side_effect=AssertionError("Must not resample")), self.assertRaisesRegex(ValueError, "identity mismatch"):
                client.complete(messages, identity["tag"])

    def test_existing_and_failed_results_are_not_reopened(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            for seed, status in (("good", "ok"), ("bad", "generation_failed")):
                run.write_json(folder / "results/framework" / seed / "00.json", [{"slot": i, "status": status, "attempts": 3} for i in range(20)])
            self.assertEqual(pending_seeds(folder, "framework", ("good", "bad", "missing")), {"missing"})

    def test_prior_http_budget_is_not_reset(self):
        with tempfile.TemporaryDirectory() as temp:
            cache = Path(temp)
            (cache / "requests.jsonl").write_text('{"event":"request_start"}\n' * 200)
            client = RecoveryClient("https://example.com/v1", "fixture", cache, max_calls=200)
            def reserve(self, identity, key):
                self._reserve_call(key, identity["tag"], 1)
                raise AssertionError("Budget should stop before HTTP")
            with patch.object(ChatClient, "_complete", reserve), self.assertRaises(APIError) as error:
                client.complete([{"role": "user", "content": "fixture"}], "framework/s/0/attempt-0")
            self.assertEqual(error.exception.kind, "call_budget_exhausted")
            self.assertEqual(client._calls, 200)


def read_json(path):
    return json.loads(path.read_text())


if __name__ == "__main__":
    unittest.main()
