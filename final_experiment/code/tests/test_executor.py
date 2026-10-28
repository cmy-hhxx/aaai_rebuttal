import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from experiment.executor import GeneratorError, _decode_output, _profile, run_generator


class ExecutorTests(unittest.TestCase):
    def test_json_answers_preserve_type(self):
        rows = [{"problem": "What?", "answer": {"a": [1, True]}, "explanation": "Because."}]
        self.assertEqual(_decode_output(json.dumps(rows), 1), rows)

    def test_rejects_bad_output(self):
        for raw in ("```json\n[]\n```", "{}", "[]", '[{"problem":"x"}]', '[{"problem":"","answer":1}]', '[{"problem":"x","answer":NaN}]'):
            with self.subTest(raw=raw), self.assertRaises(GeneratorError):
                _decode_output(raw, 1)

    def test_fail_closed_on_other_platform(self):
        with patch("experiment.executor.sys.platform", "linux"), self.assertRaisesRegex(GeneratorError, "runtime not available"):
            run_generator("print('[]')", 0, 1, Path("unused"))

    def test_profile_does_not_allow_home_or_project(self):
        profile = _profile(Path("/private/tmp/job"), Path("/Users/alice/runtime/python/bin/python3"))
        self.assertIn("(deny network*)", profile)
        self.assertIn("(deny process-fork)", profile)
        self.assertIn("(deny mach-lookup)", profile)
        self.assertIn('(literal "/")', profile)
        self.assertIn('(subpath "/Users/alice/runtime/python")', profile)
        self.assertNotIn('(subpath "/Users/alice")', profile)
        self.assertNotIn("AAAI_rebuttal", profile)

    def test_launch_has_no_secrets_and_isolated_command(self):
        def launch(command, **kwargs):
            self.assertEqual(command[0], "/usr/bin/sandbox-exec")
            self.assertIn("-P", command)
            self.assertIn("-s", command)
            self.assertTrue(kwargs["start_new_session"])
            self.assertEqual(set(kwargs["env"]), {"HOME", "TMPDIR", "PATH", "LC_ALL", "PYTHONHASHSEED"})
            self.assertEqual(kwargs["env"]["PYTHONHASHSEED"], "0")
            kwargs["stdout"].write(b'[{"problem":"p","answer":42}]')
            class Process:
                returncode = 0
                def wait(self, timeout=None):
                    return 0
            return Process()
        with tempfile.TemporaryDirectory() as folder, patch("experiment.executor.sys.platform", "darwin"), patch("experiment.executor.shutil.which", return_value="/usr/bin/sandbox-exec"), patch("experiment.executor.subprocess.Popen", side_effect=launch):
            result = run_generator("print('example')", 42, 1, Path(folder))
            self.assertEqual(result[0]["answer"], 42)

    def test_timeout_kills_process_group(self):
        class Process:
            pid = 123
            def wait(self, timeout=None):
                if timeout is not None:
                    raise subprocess.TimeoutExpired("sandbox-exec", timeout)
                return -9
        with tempfile.TemporaryDirectory() as folder, patch("experiment.executor.sys.platform", "darwin"), patch("experiment.executor.shutil.which", return_value="/usr/bin/sandbox-exec"), patch("experiment.executor.subprocess.Popen", return_value=Process()), patch("experiment.executor.os.killpg") as kill:
            with self.assertRaisesRegex(GeneratorError, "timed out"):
                run_generator("while True: pass", 0, 1, Path(folder), timeout=1)
            kill.assert_called_once()

    def test_sandbox_start_failure_never_falls_back(self):
        def launch(command, **kwargs):
            kwargs["stderr"].write(b"sandbox-exec: sandbox_init: Operation not permitted")
            class Process:
                returncode = 1
                def wait(self, timeout=None):
                    return 1
            return Process()
        with tempfile.TemporaryDirectory() as folder, patch("experiment.executor.sys.platform", "darwin"), patch("experiment.executor.shutil.which", return_value="/usr/bin/sandbox-exec"), patch("experiment.executor.subprocess.Popen", side_effect=launch) as start:
            with self.assertRaisesRegex(GeneratorError, "runtime not available"):
                run_generator("print('[]')", 0, 1, Path(folder))
            self.assertEqual(start.call_count, 1)


if __name__ == "__main__":
    unittest.main()
