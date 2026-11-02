"""Distributable license and brand assets are release gates."""

import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_license_and_brand_assets_present():
    license_text = (ROOT / "LICENSE").read_text()
    assert license_text.startswith("MIT License")
    assert "Copyright (c) 2026 Mischa Fürst" in license_text
    png = (ROOT / "brand/icon.png").read_bytes()
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    width, height = struct.unpack(">II", png[16:24])
    assert width == height and width >= 256
    assert (ROOT / "custom_components/ecoflow_smart_charge/brand/icon.png").read_bytes() == png
