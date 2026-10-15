# Binding file ownership and delivery rules

Domain is frozen as `ecoflow_smart_charge`; one integration, no new cloud client.
Existing repository and local commits are retained. No force reset or re-init.

## Core lane

Owns `custom_components/ecoflow_smart_charge/planner/**`,
`tests/test_planner.py`, `tests/unit/**`, `docs/core/**`, `docs/tdd/core/**`.
Owns all planner dataclasses and pure learning transitions defined in INTERFACE.
No edits to HA imports, storage, runtime, CI or shared root config.
Use the existing planner/core.py as the public facade; split internals freely.

## HA adapter lane

Owns integration Python files outside planner/, including __init__, const,
config_flow, runtime, storage, diagnostics and six entity platforms; new
ha_adapter/**, coordinator, commands, migration modules;
`tests/test_runtime.py`, `tests/test_safety_regressions.py`,
`tests/test_config_flow.py`, `tests/test_ha_integration.py`, `tests/ha/**`,
`tests/conftest.py`, `docs/adapter/**`, `docs/tdd/adapter/**`.
Mixed legacy safety regression file belongs ONLY to adapter (do not split it
concurrently). Pure planning additions belong to core's tests/unit instead.
Adapter alone owns runtime service/entity keys and documents their inventory in
docs/adapter/ENTITY-SERVICE-CONTRACT.md for packaging to consume.

## Packaging lane

Owns README, LICENSE/attributions, hacs.json, manifest.json, strings.json,
translations/**, services.yaml, brand/**, .github/**, pyproject.toml,
requirements*.txt, requirements*.lock, .gitignore, tools/** (except foundation
runner), docs/release/**, docs/migration/**, docs/tdd/packaging/**,
`tests/packaging/**`. Do not change adapter Python to match invented translations.
Consume adapter's key inventory; if not ready, prepare packaging with existing
keys and leave final schema alignment to the integration lane after both finish.
The integration/reconciliation lane owns final cross-file corrections and final
CI/package validation, not parallel opportunistic edits.

## Frozen foundation

`docs/foundation/**`, `tests/foundation/**`, `tools/run_tests.py` and
requirements-test.lock are frozen after this handoff; reconcile changes in the
integration lane. Each lane writes a separate test/parity report, referencing row
IDs from PARITY.md; do not have three workers update one shared checklist.

No worker runs `git add .`, `git commit -a`, resets, cleans or checks out branches
in this shared working copy. Stage ONLY owned files and commit explicitly; do
not include another lane's uncommitted files. Read git status before and after.
Interface changes require a board comment to both core and adapter and agreement
before edits. Mention any collision as `hotspot: path — reason`.

All implementation lanes must load test-driven-development, follow vertical
RED/GREEN/REFACTOR and use the common log format. No publication, live HA change,
source-repo writes, direct .storage changes or hardware exercises in these lanes.
