"""CI must execute the same locked, offline product tests as local checks."""

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def test_ci_pins_actions_and_uses_locked_test_runner():
    source = (ROOT / ".github/workflows/validate.yml").read_text()
    workflow = yaml.safe_load(source)
    assert workflow.get("permissions") == {"contents": "read"}
    assert {"tests", "hacs", "hassfest"} <= set(workflow["jobs"])
    steps = [s for job in workflow["jobs"].values() for s in job["steps"]]
    for step in steps:
        if "uses" in step:
            assert re.search(r"@[0-9a-f]{40}$", step["uses"]), step["uses"]
    commands = "\n".join(s.get("run", "") for s in steps)
    assert "--require-hashes -r requirements-test.lock" in commands
    assert "python tools/run_tests.py" in commands
    assert "python -m ruff check ." in commands
    assert "python -m ruff format --check ." in commands
    assert "requirements-lint.txt" in commands
    assert "python-version: '3.14.7'" in source
    assert "comment: false" in source
