"""Whole planner package can execute with only the Python standard library."""

import subprocess
import sys
from pathlib import Path


def test_complete_planner_package_without_site_packages_or_ha():
    planner = Path(__file__).resolve().parents[2] / "custom_components/ecoflow_smart_charge/planner"
    code = """
import importlib, sys, types
package=types.ModuleType('isolated_planner')
package.__path__=[sys.argv[1]]
sys.modules[package.__name__]=package
core=importlib.import_module('isolated_planner.core')
learning=importlib.import_module('isolated_planner.learning')
forecast=importlib.import_module('isolated_planner.forecast')
assert core.Battery(50,7).reserve==7
assert learning.PVLearningState((),1,None,None,None).correction==1
assert not any(name.startswith('homeassistant') for name in sys.modules)
print('entire pure planner imported without HA/site packages')
"""
    result = subprocess.run(
        [sys.executable, "-S", "-c", code, str(planner)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "entire pure planner imported" in result.stdout
