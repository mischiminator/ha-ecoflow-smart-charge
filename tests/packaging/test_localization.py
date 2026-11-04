"""Check shipped locale structure and explicit entry-targeted action forms."""

from __future__ import annotations

import ast
import json
from pathlib import Path

import yaml

COMPONENT = Path(__file__).resolve().parents[2] / "custom_components/ecoflow_smart_charge"


def leaf_keys(value, prefix=""):
    """Enumerate language-independent JSON paths."""
    return {
        path
        for key, child in value.items()
        for path in (
            leaf_keys(child, f"{prefix}{key}.") if isinstance(child, dict) else {f"{prefix}{key}"}
        )
    }


def test_fields_match_actual_adapter_schema():
    """Read schema literals without importing HA or running integration setup."""
    tree = ast.parse((COMPONENT / "config_flow.py").read_text())
    mapping = {}
    for node in tree.body:
        if (
            isinstance(node, ast.Assign)
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == "FIELDS"
        ):
            mapping.update(dict.fromkeys(ast.literal_eval(node.value)))
    assert mapping, "adapter no longer exposes expected source mapping schema"
    strings = json.loads((COMPONENT / "strings.json").read_text())
    fields = set(mapping)
    assert set(strings["config"]["step"]["user"]["data"]) == fields
    assert set(strings["config"]["step"]["reconfigure"]["data"]) == fields
    services = yaml.safe_load((COMPONENT / "services.yaml").read_text())
    assert set(services) == {"recalculate"}
    assert set(services["recalculate"]["fields"]) == {"config_entry_id"}


def test_complete_matching_locales_and_service_fields():
    assert (COMPONENT / "strings.json").is_file(), "canonical English strings missing"
    strings = json.loads((COMPONENT / "strings.json").read_text())
    en = json.loads((COMPONENT / "translations/en.json").read_text())
    de = json.loads((COMPONENT / "translations/de.json").read_text())
    assert strings == en
    assert leaf_keys(en) == leaf_keys(de)
    assert "config.error.battery_count_invalid" in leaf_keys(en)
    assert "config.abort.already_configured" in leaf_keys(en)
    services = yaml.safe_load((COMPONENT / "services.yaml").read_text())
    assert set(services) == set(en["services"])
    for name, service in services.items():
        assert "name" in en["services"][name]
        assert "description" in en["services"][name]
        assert service["fields"]["config_entry_id"]["required"] is True
        assert set(service["fields"]) == set(en["services"][name]["fields"])
        assert "config_entry" in service["fields"]["config_entry_id"]["selector"]
