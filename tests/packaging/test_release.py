"""Release workflow: validated, version-checked, least-privilege, notes from the changelog."""

import re
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

import release


def test_release_workflow_validates_first_and_only_release_job_can_write():
    workflow = yaml.safe_load((ROOT / ".github/workflows/release.yml").read_text())
    assert workflow["on"] == {"push": {"tags": ["v*.*.*"]}}
    assert workflow["permissions"] == {"contents": "read"}
    jobs = workflow["jobs"]
    assert jobs["validate"]["uses"] == "./.github/workflows/validate.yml"
    assert jobs["release"]["needs"] == "validate"
    assert jobs["release"]["permissions"] == {"contents": "write"}
    steps = jobs["release"]["steps"]
    for step in steps:
        if "uses" in step:
            assert re.search(r"@[0-9a-f]{40}$", step["uses"]), step["uses"]
    commands = "\n".join(s.get("run", "") for s in steps)
    assert 'python tools/release.py "$GITHUB_REF_NAME"' in commands
    assert "--verify-tag" in commands and "ecoflow_smart_charge.zip" in commands
    validate = yaml.safe_load((ROOT / ".github/workflows/validate.yml").read_text())
    assert "workflow_call" in validate["on"]


def test_shipped_version_has_changelog_notes(capsys):
    manifest, _ = release.versions()
    release.main(f"v{manifest}")
    out = capsys.readouterr().out
    assert out.strip() and "## [" not in out


@pytest.mark.parametrize("tag", ["1.0.0", "v1.0", "v9.9.9"])
def test_mismatched_or_malformed_tags_are_refused(tag):
    with pytest.raises(SystemExit):
        release.main(tag)


def test_notes_stop_at_the_next_version():
    text = "## [2.0.0] - x\nnew\n\n## [1.0.0] - y\nold\n"
    assert release.notes("2.0.0", text) == "new"
    assert release.notes("1.0.0", text) == "old"
    assert release.notes("3.0.0", text) == ""
