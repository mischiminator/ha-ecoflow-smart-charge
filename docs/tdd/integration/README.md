# Integration reconciliation: executed vertical evidence

Scope: final local integration only; no live HA, hardware, publication or storage edits.
The TDD skill was loaded before changes. Parent core/adapter/packaging TDD evidence
remains under the sibling directories; it is not replaced by this report.

## I01 — preserve complete pure-package isolation

RED: `evidence/integration-baseline.log` and XML: 221 passed / 1 failed.
The foundation loader treated core.py as a standalone module; legitimate relative
imports failed. This was a test-harness defect, not missing production fallback.
GREEN: `evidence/integration-foundation-green.log`: both foundation tests pass.
The repaired test AST-checks every planner module and imports all modules in a
neutral package namespace in a real `python -S` subprocess. It neither imports
the HA integration initializer nor installs fake HA modules. No planner code changed.
Ruff baseline separately recorded the three frozen foundation/runner formatting
issues; only import order and formatting were changed there.

## I02 — connect all six platform translations

Test first: real HA entry setup and entity-registry readback compare every native
unique-id key with all three shipped localization inventories and translation_key.
RED: `evidence/integration-locale-red.log`: number minimum_price_advantage has
translation_key=None. Existing locale inventory also omitted four sensors and
session_active. GREEN: `evidence/integration-locale-green.log`: one real HA test
passes after RuntimeEntity supplies translation_key (instead of a fixed English
name), and canonical EN, generated EN and DE receive the five missing keys.
Stable unique IDs are unchanged; existing registry entity IDs remain operator-owned.
Entity names on new installs can be localized; raw reason/status codes remain codes.

## I03 — redact identifiers and handle unavailable/blocked diagnostics

`test_release_alignment::test_diagnostics_never_disclose_entry_or_nested_canaries`
creates real HA entries in shadow, active, pending, blocked and uninitialized states.
RED: `evidence/integration-diagnostics-red.log`: raw config-entry ID leaked in four
states; uninitialized runtime raised AttributeError. Minimal fix removes the ID and
uses a safe optional runtime lookup. A further explicit blocked-journal assertion
failed (`evidence/integration-diagnostics-blocked-red.log`): recovery_pending was
false for blocked-without-record. It now includes the journal's blocked flag.
GREEN: `evidence/integration-diagnostics-green.log`: all six alignment/diagnostic
cases pass. Synthetic entry/options/nested/session/error canaries never serialize.
Tests exercise the real custom diagnostics handler, not the authenticated HTTP/UI
export wrapper; that distinction remains documented rather than invented.

## I04 — additional acceptance coverage, not new implementation

`tests/ha/test_release_recovery.py` cancels after each of five actually completed
journal saves: initial capture, phase save, and each per-target intent. It recreates
a Runtime from disk, checks restart is passive shadow, requires explicit recovery,
keeps two-of-three readback pending, retries only the third after 30 seconds, and
clears only after its fresh readback. A full-marker persistence failure emits no
restoration commands. These passed on first execution: acceptance tests of existing
parent implementation, NOT a fabricated failed-first feature cycle.

The real HA source-reader/core/store/transport service-chain test now runs both
one and four concurrent service requests; both produce only three initial hardware
transport invocations, retain originals, interlock conflicting legacy writers and
complete independent readback. Transport is synthetic; no physical battery changed.
Executed scoped log: `evidence/integration-recovery-acceptance.log` (8 passed).

## Final gates

See ../../release/INTEGRATION-REPORT.md and ../../release/PARITY-FINAL.md.
The final full suite, Ruff and official source hassfest are rerun after integration.
Full HACS action, public-history cleanup, live commissioning and source-rights review
remain explicit external release gates, not passing local tests.
