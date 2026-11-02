"""Check a release tag against the shipped version and print its changelog section."""

import json
import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def versions():
    manifest = json.loads(
        (ROOT / "custom_components/ecoflow_smart_charge/manifest.json").read_text()
    )
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    return manifest["version"], project["version"]


def notes(version, changelog):
    """The body under "## [version]" up to the next version heading."""
    match = re.search(
        rf"^## \[{re.escape(version)}\][^\n]*\n(.*?)(?=^## \[|\Z)",
        changelog,
        re.MULTILINE | re.DOTALL,
    )
    return match.group(1).strip() if match else ""


def main(tag):
    if not re.fullmatch(r"v\d+\.\d+\.\d+", tag):
        raise SystemExit(f"tag {tag!r} is not vMAJOR.MINOR.PATCH")
    version = tag[1:]
    if set(versions()) != {version}:
        raise SystemExit(f"tag {tag} does not match manifest/pyproject versions {versions()}")
    body = notes(version, (ROOT / "CHANGELOG.md").read_text())
    if not body:
        raise SystemExit(f"CHANGELOG.md has no section for {version}")
    print(body)


if __name__ == "__main__":
    main(sys.argv[1])
