# Core task retry verification

The earlier run reached local commit `506ad630eaac05a0a20fa52e7bbcbb75882126d0`
but exhausted its iteration budget before the board completion transition.
This retry inspected the committed implementation, upstream contracts, provenance
and vertical RED/GREEN evidence rather than replacing completed work.
No production implementation changes were needed.

Executed again with the foundation interpreter:

    python tools/run_tests.py tests/unit tests/test_planner.py -q --junitxml=docs/tdd/core/retry-tests.xml

Result:148 passed,0 failed,0 errors,0 skipped;1.76 seconds.
The runner disables IP sockets and allows Unix sockets for the HA test plugin.
This includes48 exact captured-Jinja oracle cases and the child python -S
whole-planner import probe. XML is retained beside this report.

Executed scoped lint and formatting via packaging's pinned tool:

    uvx --from ruff==0.17.0 ruff check custom_components/ecoflow_smart_charge/planner tests/unit tests/test_planner.py
    uvx --from ruff==0.17.0 ruff format --check custom_components/ecoflow_smart_charge/planner tests/unit tests/test_planner.py
    git diff --check

All passed;16 files already formatted. An initial attempt to run Ruff through
`python -m ruff` failed because Ruff is deliberately not installed in the frozen
HA harness; the successful pinned uvx invocation did not modify that harness.

Recomputed SHA256 for all eight foundation-ledger source files: all unchanged.
Both sanitized fixture SHA256 values match docs/core/PROVENANCE.md.

## Shared-tree regression is not accepted

A fresh `python tools/run_tests.py -q --tb=short` during sibling adapter work
returned202 passed/4 failed, rather than the previous run's202 passed/1 failed:

- Frozen foundation isolation loader imports core.py as an unrelated standalone
  module without a parent package; relative imports fail. Correct the loader in
  reconciliation; do not add production import-path hacks. The owned python -S
  complete-package probe passes.
- HA PV statistics normalization test: read_daily_pv raises
  pv_statistics_unit_invalid for its Wh fixture.
- HA sampling test: new probe remains None rather than6 without yesterday data.
- HA entry lifecycle assertion expects shadow, receives shadow_recalculated.

The last three findings are adapter-owned; all four were communicated to the
existing adapter/reconciliation cards. No sibling or frozen files were edited.
This is core-phase completion, not whole-integration/release/cutover approval.
No production HA commands, source edits, GitHub publication or history rewrite.
