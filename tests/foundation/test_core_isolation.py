"""The complete planner must remain importable without HA or site packages."""

import ast
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLANNER = ROOT / "custom_components/ecoflow_smart_charge/planner"


class IsolationTests(unittest.TestCase):
    def test_existing_core_import_has_no_homeassistant_dependency(self):
        for source in PLANNER.glob("*.py"):
            tree = ast.parse(source.read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    self.assertFalse((node.module or "").startswith("homeassistant"))
                if isinstance(node, ast.Import):
                    self.assertTrue(
                        all(not item.name.startswith("homeassistant") for item in node.names)
                    )
        # A neutral package path permits legitimate internal relative imports,
        # without importing the HA integration initializer or faking HA modules.
        code = """
import importlib, pathlib, sys, types
package = types.ModuleType('foundation_isolated_planner')
package.__path__ = [sys.argv[1]]
sys.modules[package.__name__] = package
for source in pathlib.Path(sys.argv[1]).glob('*.py'):
    if source.stem != '__init__':
        importlib.import_module(package.__name__ + '.' + source.stem)
core = importlib.import_module(package.__name__ + '.core')
assert core.Battery(50, 7).reserve == 7
assert not any(name.startswith('homeassistant') for name in sys.modules)
"""
        result = subprocess.run(
            [sys.executable, "-S", "-c", code, str(PLANNER)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
