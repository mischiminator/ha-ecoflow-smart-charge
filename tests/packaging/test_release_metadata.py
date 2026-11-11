"""Offline release structure checks, not substitutes for HACS/hassfest."""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COMPONENT = ROOT / "custom_components" / "ecoflow_smart_charge"


def test_release_metadata_declares_tested_compatibility():
    """Prevent offering this Python 3.14 integration to incompatible HA installs."""
    manifest = json.loads((COMPONENT / "manifest.json").read_text())
    hacs = json.loads((ROOT / "hacs.json").read_text())
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    assert hacs.get("homeassistant") == "2026.10.1"
    assert manifest["version"] == project["version"] == "1.0.7"
    assert manifest["domain"] == COMPONENT.name
    assert manifest["config_flow"] is True
    assert manifest["integration_type"] == "service"
    assert manifest["iot_class"] == "local_push"
    assert manifest["codeowners"] == ["@mischiminator"]
    assert manifest.get("requirements", []) == []
    # frontend/http only serve the bundled card; the integration runs without them.
    assert manifest.get("after_dependencies") == ["frontend", "http", "recorder"]
    assert set(manifest) >= {"documentation", "issue_tracker", "name", "version"}
    domains = [
        p.name for p in COMPONENT.parent.iterdir() if p.is_dir() and not p.name.startswith("_")
    ]
    assert domains == ["ecoflow_smart_charge"]
