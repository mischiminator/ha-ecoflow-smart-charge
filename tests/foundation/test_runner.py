"""Plain pytest runs offline, the same way locally and in CI."""

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_pytest_disables_ip_sockets_by_default():
    options = tomllib.loads((ROOT / "pyproject.toml").read_text())["tool"]["pytest"]["ini_options"]
    assert "--disable-socket" in options["addopts"]
    assert "--allow-unix-socket" in options["addopts"]
