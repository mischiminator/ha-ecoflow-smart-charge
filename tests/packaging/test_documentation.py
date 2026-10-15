"""Safety documentation and distributable assets are release gates."""

import json
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_migration_documents_make_safe_recovery_order_explicit():
    required = [
        "docs/migration/MIGRATION-DE.md",
        "docs/migration/MIGRATION-EN.md",
        "docs/migration/CARD-COMPATIBILITY.md",
        "docs/release/DIAGNOSTICS.md",
        "docs/release/VALIDATION.md",
        "docs/release/PROVENANCE.md",
        "docs/release/RELEASE-CHECKLIST.md",
    ]
    assert all((ROOT / name).is_file() for name in required), "missing release runbooks"
    en = (ROOT / required[1]).read_text()
    assert "OUTSIDE shadow" in en
    assert "A service ACK/HTTP success is not readback" in en
    assert "BOTH charging writers off" in en
    assert "Never directly edit `.storage`" in en
    assert "20% is ONLY a new-install default" in en
    card = (ROOT / required[2]).read_text()
    assert "input_boolean.turn_on/turn_off" in card
    assert "input_number.set_value" in card
    assert "battery slots 0..2" in card
    assert "not an implemented card patch" in card


def test_synthetic_import_example_is_accepted_by_real_validator():
    path = ROOT / "docs/migration/examples/inactive-import.json"
    assert path.is_file(), "missing versioned synthetic import example"
    from custom_components.ecoflow_smart_charge.migration import validate_import

    payload = json.loads(path.read_text())
    settings, learning, marker, session = validate_import(payload, ())
    assert settings == payload["settings"]
    assert learning == payload["learning"]
    assert marker is None and session is None
    assert settings["mode"] == "shadow" and settings["master"] is False


def test_license_and_brand_assets_present():
    license_text = (ROOT / "LICENSE").read_text()
    assert license_text.startswith("MIT License")
    assert "Copyright (c) 2026 Mischa Fürst" in license_text
    png = (ROOT / "brand/icon.png").read_bytes()
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    width, height = struct.unpack(">II", png[16:24])
    assert width == height and width >= 256
