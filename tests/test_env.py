import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from experiment.env import load_env


class EnvTests(unittest.TestCase):
    def test_literal_values_no_execution_and_existing_environment_kept(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {"PRESERVE": "existing"}, clear=True):
            p = Path(tmp) / ".env"
            p.write_text('# note\nexport TEST_KEY="literal$(command)"\nPRESERVE=new\nTEST_URL=https://example.test/v1\n')
            load_env(p)
            self.assertEqual(os.environ["TEST_KEY"], "literal$(command)")
            self.assertEqual(os.environ["PRESERVE"], "existing")
            self.assertEqual(os.environ["TEST_URL"], "https://example.test/v1")

    def test_invalid_assignment_does_not_echo_value(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / ".env"
            p.write_text("bad key=SECRET\n")
            with self.assertRaises(ValueError) as caught:
                load_env(p)
            self.assertNotIn("SECRET", str(caught.exception))
