# Reproducible local starting point

Existing local scaffold is preserved, not overwritten. Domain and boundaries are
frozen by OWNERSHIP.md and INTERFACE.md. No remote is configured by foundation.
The baseline is NOT a deployable or parity-complete controller. In particular
runtime restoration currently has an unguarded shadow path and must be fixed by
the adapter using failed-first tests; the README safety claims are requirements,
not verified broad guarantees. Recorder, tariff parsing and projection need work.

Validated dependency target: Python3.14.7 (HA requires >=3.14.2),
Home Assistant2026.10.1, pytest-homeassistant-custom-component0.13.372,
pytest9.0.3. requirements-test.lock contains exact transitive pins and hashes
from the verified isolated harness, with machine-specific generation comments
removed. It does not install the integration in production.

    uv venv --python 3.14.7 .venv
    uv pip sync --python .venv/bin/python --require-hashes requirements-test.lock
    .venv/bin/python tools/run_tests.py
    .venv/bin/python tools/run_tests.py tests/test_planner.py -q
    .venv/bin/python -m unittest discover -s tests/foundation -v

Use an existing compatible isolated interpreter if supplied by the local handoff;
do not recreate it or modify system Python. The runner forwards pytest arguments,
returns pytest's exit status and disables IP sockets. Do not run the runner test
itself with -s inside a nested recursive invocation; it tests --version only.
No live network/device permission is needed for baseline tests. Pure core tests
can additionally use unittest/importlib without installing HA; adapter must keep
the import boundary free of eager HA setup. Test runner expects pytest-socket,
provided by the lock; missing dependency is a setup error, not a product pass.

Current tests are mostly scaffold regressions. Populated Recorder/DST/unit,
conflict, crash and every full parity row remain downstream requirements.
HACS/Hassfest/ruff and final packaging validation belong to packaging/reconcile.
Each lane stages only owned files in this shared working copy. Keep snapshots,
private mappings and raw logs out of the repo. No git publication or HA install.

Before publication, packaging must sanitize history: earlier scaffold commits
already contained a household-specific source ID and migration values in README.
Foundation removes them from the current README, not by destructive history
rewrite while workers share this repository. Publish only sanitized history after
explicit review; existing local history must not be pushed as-is.
