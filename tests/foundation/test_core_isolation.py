"""Existing core must remain importable without HA or site packages."""
import ast
import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
CORE = ROOT / "custom_components/ecoflow_smart_charge/planner/core.py"


class IsolationTests(unittest.TestCase):
    def test_existing_core_import_has_no_homeassistant_dependency(self):
        tree = ast.parse(CORE.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                self.assertFalse((node.module or "").startswith("homeassistant"))
            if isinstance(node, ast.Import):
                self.assertTrue(all(not item.name.startswith("homeassistant") for item in node.names))
        name = "foundation_isolated_core"
        spec = importlib.util.spec_from_file_location(name, CORE)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        try:
            spec.loader.exec_module(module)
            self.assertEqual(module.Battery(50, 7).reserve, 7)
        finally:
            del sys.modules[name]
