"""Test the real local test entry point, without Home Assistant fixtures."""
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "tools" / "run_tests.py"


class RunnerTests(unittest.TestCase):
    def test_runner_invokes_pytest_from_an_unrelated_directory(self):
        self.assertTrue(RUNNER.is_file(), "reproducible test entry point is missing")
        result = subprocess.run(
            [sys.executable, str(RUNNER), "--version"],
            cwd=ROOT.parent, capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("pytest", result.stdout)
