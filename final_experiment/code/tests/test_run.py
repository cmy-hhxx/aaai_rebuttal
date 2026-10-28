import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from experiment.run import ROOT, export, generate, parse_rows, prepare, prompt_paths, seed_for
from experiment.executor import GeneratorError


class RunTests(unittest.TestCase):
    @unittest.skipUnless((ROOT / "sources/puzzleforge_supplement/data/seed_puzzles.jsonl").exists(),
                         "Private author data is not distributed with the public code")
    def test_actual_sources_and_frozen_cohorts(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            config = ROOT / "configs/experiment.example.json"
            m = prepare(config, out)
            records = json.loads((out / "reference.json").read_text())
            seeds = json.loads((out / "seeds.json").read_text())
            self.assertEqual(len(records), 1720)
            self.assertEqual(sum(map(len, m["matched_slots"].values())), 1720)
            self.assertEqual(len({r["id"] for r in records}), 1720)
            self.assertEqual(len(seeds), 129)
            self.assertEqual((out / "snapshot/experiment/run.py").read_bytes(), (ROOT / "experiment/run.py").read_bytes())
            self.assertTrue(any(not isinstance(s["answer"], str) for s in seeds))
            self.assertEqual(prepare(config, out), m)
            changed = json.loads(config.read_text())
            changed["rng_seed"] += 1
            other = out / "other.json"
            other.write_text(json.dumps(changed))
            with self.assertRaisesRegex(ValueError, "Frozen run changed"):
                prepare(other, out)

    def test_schema_and_source_mapping(self):
        self.assertEqual(seed_for("time_sequence_0", {"time_sequence"}), "time_sequence")
        with self.assertRaises(ValueError):
            seed_for("unknown_0", {"time_sequence"})
        row = {"problem": "A puzzle", "answer": [1, 2], "explanation": "A check"}
        self.assertEqual(parse_rows(json.dumps([row]), 1), [row])
        with self.assertRaises(ValueError):
            parse_rows(json.dumps([row]), 2)

    def test_direct_resume_and_no_pf_output_in_prompt(self):
        calls = []

        class FakeClient:
            def __init__(self, *args):
                pass

            def complete(self, messages, tag):
                calls.append(messages)
                request = json.loads(messages[-1]["content"])
                content = [{"problem": f"fake {tag}/{i}", "answer": i, "explanation": "test fixture"}
                           for i in range(request["count"])]
                return {"model": "mock", "choices": [{"message": {"content": json.dumps(content)}}]}

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            c = json.loads((ROOT / "configs/experiment.example.json").read_text())
            c["endpoint"] = "http://localhost/v1"
            (out / "seeds.json").write_text(json.dumps([{"id": "s", "question": "seed only", "answer": 3}]))
            m = {"config": c, "matched_slots": {"s": list(range(16))}}
            with patch("experiment.run.ChatClient", FakeClient):
                generate(m, out, "direct")
                generate(m, out, "direct")
            self.assertEqual(len(calls), 4)
            self.assertEqual(json.loads(calls[0][1]["content"])["seed_question"], "seed only")
            expected_system = (ROOT / "experiment/prompts/quality.txt").read_text() + "\n" + (ROOT / "experiment/prompts/direct.txt").read_text()
            self.assertEqual(calls[0][0]["content"], expected_system)
            self.assertNotIn("output_language", json.loads(calls[0][-1]["content"]))
            records = [r for p in (out / "results").glob("*/*/*.json") for r in json.loads(p.read_text())]
            self.assertEqual(len(records), 20)
            self.assertEqual(sum(r["cohort"] == "matched" for r in records), 16)

    def test_framework_invalid_explanation_is_not_saved_as_success(self):
        class FakeClient:
            def __init__(self, *args):
                pass

            def complete(self, messages, tag):
                return {"model": "mock", "choices": [{"message": {"content": "# fixture code"}}]}

        def fake_executor(code, seed, count, work_dir, **kwargs):
            return [{"problem": "fixture", "answer": 0} for _ in range(count)]

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            c = json.loads((ROOT / "configs/experiment.example.json").read_text())
            c["endpoint"] = "http://localhost/v1"
            (out / "seeds.json").write_text(json.dumps([{"id": "s", "question": "seed", "answer": 3}]))
            with patch("experiment.run.ChatClient", FakeClient), patch("experiment.run.run_generator", fake_executor):
                generate({"config": c, "matched_slots": {"s": list(range(16))}}, out, "framework")
            records = json.loads((out / "results/framework/s/00.json").read_text())
            self.assertTrue(all(r["status"] == "generation_failed" for r in records))

    def test_framework_repair_prompt_is_persisted_without_random_job_path(self):
        calls = []
        class FakeClient:
            def __init__(self, *args):
                pass

            def complete(self, messages, tag):
                calls.append(messages)
                return {"model": "mock", "choices": [{"message": {"content": "# fixture"}}]}

        def fake_executor(code, seed, count, work_dir, **kwargs):
            if count == 1:
                return [{"problem": "probe", "answer": 0}]
            raise GeneratorError(f"job={work_dir}/generator-RANDOM_TOKEN\nValueError: test failure")

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            c = json.loads((ROOT / "configs/experiment.example.json").read_text())
            c["endpoint"] = "http://localhost/v1"
            (out / "seeds.json").write_text(json.dumps([{"id": "s", "question": "seed", "answer": 3}]))
            with patch("experiment.run.ChatClient", FakeClient), patch("experiment.run.run_generator", fake_executor):
                generate({"config": c, "matched_slots": {"s": list(range(16))}}, out, "framework")
            second = json.loads((out / "traces/framework/s/0/attempt-1.json").read_text())
            self.assertIn("<GENERATOR_JOB>", second[-1]["content"])
            self.assertNotIn("RANDOM_TOKEN", json.dumps(second))

    def test_paper_v2_system_language_and_source_integrity(self):
        for method in ("direct", "framework"):
            for language, output_language in (("zh", "en"), ("en", "zh")):
                with self.subTest(method=method, language=language), tempfile.TemporaryDirectory() as tmp:
                    out = Path(tmp)
                    c = json.loads((ROOT / "configs/experiment.example.json").read_text())
                    c.update(endpoint="http://localhost/v1", prompt_variant="paper_v2", prompt_language=language, output_language=output_language)
                    source = {"id": "s", "question": "A general puzzle: keep p1 and literal ABC unchanged.", "answer": {"valid": [True, 3], "label": "[[ABC]]"}}
                    (out / "seeds.json").write_text(json.dumps([source]))
                    live_path = prompt_paths(c, method)[0]
                    expected_system = live_path.read_text()
                    relative = str(live_path.relative_to(ROOT))
                    frozen = out / "snapshot" / relative
                    frozen.parent.mkdir(parents=True)
                    frozen.write_text(expected_system)
                    m = {"config": c, "matched_slots": {"s": list(range(16))}, "input_hashes": {relative: hashlib.sha256(expected_system.encode()).hexdigest()}}
                    calls = []

                    class FakeClient:
                        def __init__(self, *args):
                            pass

                        def complete(self, messages, tag):
                            calls.append(messages)
                            request = json.loads(messages[-1]["content"])
                            rows = [{"problem": f"fixture {tag}/{i}", "answer": i, "explanation": "fixture"} for i in range(request.get("count", 0))]
                            return {"model": "mock", "choices": [{"message": {"content": json.dumps(rows) if method == "direct" else "# fixture; not executed"}}]}

                    def fake_executor(code, seed, count, work_dir, **kwargs):
                        return [{"problem": f"fixture {seed}/{i}", "answer": i, "explanation": "fixture"} for i in range(count)]

                    real_read = Path.read_text

                    def forbid_live_prompt(path, *args, **kwargs):
                        if path == live_path:
                            raise AssertionError("A prepared run must not read its live prompt")
                        return real_read(path, *args, **kwargs)

                    with patch("experiment.run.ChatClient", FakeClient), patch("experiment.run.run_generator", fake_executor), patch.object(Path, "read_text", forbid_live_prompt):
                        generate(m, out, method)
                    self.assertEqual(len(calls), 4 if method == "direct" else 1)
                    for messages in calls:
                        self.assertEqual(messages[0], {"role": "system", "content": expected_system})
                        self.assertEqual(json.loads(messages[1]["content"]), {"seed_question": source["question"], "seed_answer": source["answer"]})
                        self.assertEqual(json.loads(messages[-1]["content"])["output_language"], output_language)
                    records = [r for p in (out / "results" / method / "s").glob("*.json") for r in json.loads(p.read_text())]
                    self.assertEqual(len(records), 20)
                    self.assertTrue(all(r["status"] == "ok" for r in records))

    @unittest.skipUnless((ROOT / "sources/puzzleforge_supplement/data/seed_puzzles.jsonl").exists(),
                         "Private author data is not distributed with the public code")
    def test_paper_v2_freezes_selected_prompts_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            c = json.loads((ROOT / "configs/experiment.example.json").read_text())
            c.update(prompt_variant="paper_v2", prompt_language="zh", output_language="zh")
            config = root / "config.json"
            config.write_text(json.dumps(c))
            out = root / "run"
            manifest = prepare(config, out)
            tracked = {path for path in manifest["input_hashes"] if path.startswith("experiment/prompts/")}
            expected = {str(prompt_paths(c, method)[0].relative_to(ROOT)) for method in ("direct", "framework")}
            self.assertEqual(tracked, expected)
            for path in expected:
                self.assertEqual((out / "snapshot" / path).read_bytes(), (ROOT / path).read_bytes())

    def test_bad_prompt_config_is_rejected(self):
        for extra in ({"prompt_variant": "typo"}, {"prompt_variant": "paper_v2", "prompt_language": "xx"}, {"prompt_variant": "paper_v2", "output_language": "xx"}):
            for method in ("direct", "framework"):
                with self.subTest(extra=extra, method=method), self.assertRaises(ValueError):
                    prompt_paths(extra, method)

    def test_missing_or_changed_snapshot_fails_before_execution_or_client(self):
        for method in ("direct", "framework"):
            for missing in (False, True):
                with self.subTest(method=method, missing=missing), tempfile.TemporaryDirectory() as tmp:
                    out = Path(tmp)
                    c = {"prompt_variant": "paper_v2", "prompt_language": "zh", "output_language": "zh"}
                    live = prompt_paths(c, method)[0]
                    relative = str(live.relative_to(ROOT))
                    m = {"config": c, "input_hashes": {relative: hashlib.sha256(live.read_bytes()).hexdigest()}}
                    if not missing:
                        frozen = out / "snapshot" / relative
                        frozen.parent.mkdir(parents=True)
                        frozen.write_text("tampered prompt")
                    with patch("experiment.run.ChatClient") as client, patch("experiment.run.run_generator") as executor:
                        with self.assertRaisesRegex(ValueError, "Frozen prompt missing or changed"):
                            generate(m, out, method)
                        client.assert_not_called()
                        executor.assert_not_called()

    def test_export_filters_selected_seeds_to_named_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            rows = [{"id": f"puzzleforge/{seed}/{slot}", "method": "puzzleforge", "seed_id": seed,
                     "slot": slot, "status": "ok", "cohort": "matched"}
                    for seed in ("s1", "s2") for slot in range(2)]
            (out / "reference.json").write_text(json.dumps(rows))
            (out / "results/direct/s1").mkdir(parents=True)
            (out / "results/direct/s1/00.json").write_text(json.dumps([
                {"id": "direct/s1/0", "method": "direct", "seed_id": "s1", "slot": 0,
                 "status": "ok", "cohort": "matched"}]))
            path = export(out, {"s1"}, "records_selected.jsonl")
            exported = [json.loads(line) for line in path.read_text().splitlines()]
            self.assertEqual(path.name, "records_selected.jsonl")
            self.assertEqual({row["seed_id"] for row in exported}, {"s1"})
            self.assertEqual(len(exported), 3)
            with self.assertRaisesRegex(ValueError, "plain file name"):
                export(out, None, "../escape.jsonl")


if __name__ == "__main__":
    unittest.main()
