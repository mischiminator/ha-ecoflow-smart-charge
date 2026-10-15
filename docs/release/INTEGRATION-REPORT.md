# Final local integration report

Status: locally integrated implementation candidate; independent read-only review
is the next pre-created task. NOT authorization for publication, installation,
active cutover or physical battery testing. Final exact HEAD, archive SHA256 and
archive smoke logs are recorded in the private task handoff after this report's
commit (a file cannot embed its own commit hash).

## What changed during reconciliation

- Preserved and integrated parent planner, HA adapter and packaging commits;
  existing shared tree was clean at start. No destructive rebase/reset/history rewrite.
- Fixed the foundation test's obsolete standalone-file core loader by checking
  every pure planner module in a real Python -S package import. Production planner
  imports were not hacked. Foundation/runner import ordering/format now pass Ruff.
- Connected all six native platforms to supported HA translation keys, retaining
  stable unique IDs; completed EN/DE names for all actual keys. Current flow,
  OptionsFlow, reconfigure fields and five services match metadata through AST
  schema tests plus the real entity registry/service tests.
- Removed raw config-entry identifiers from diagnostics; uninitialized runtime
  no longer raises; blocked journals correctly remain recovery_pending. Synthetic
  nested/entry/options/session/error canaries are excluded in five handler phases.
- Added acceptance probes for five durable-save crash boundaries, independent
  two-of-three readback, limited single-target retries and marker persistence
  failure. Four concurrent actual HA recalculate requests create only three start
  transport calls, preserve originals and restore through the same gatekeeper.
- Corrected operational translation docs. Historical lane reports/logs are retained
  as dated evidence; this report and PARITY-FINAL.md supersede their unresolved
  loader/translation/setup-schema warnings, not their external safety limits.

## Executed results

| Gate | Actual local result | Evidence below evidence/ |
|---|---|---|
| Whole product pytest |235 passed; failures0/errors0/skips0; HA2026.10.1, plugin0.13.372, Python3.14.7 | final-tests.log/xml |
| Offline packaging subset |7 passed | final-packaging.log |
| Whole-tree Ruff0.17.0 | check PASS; format check PASS | final-ruff.log, final-format.log |
| git diff --check | PASS | task handoff |
| Official source hassfest | Exit0;1 integration,0 invalid; all23 validators, no warnings | final-hassfest.log |
| Official full HACS action | NOT EXECUTED / OPEN: Docker absent, no authorized public repository | final-hacs.json |

Product tests disable IP sockets and allow only Unix sockets for the HA harness.
Real HA ConfigFlow/OptionsFlow/setup/reload/disable/unload, service registry,
entity registry and populated SQLite Recorder execute. Deliberate transport doubles
avoid live hardware. No FakeHass-only acceptance. Pure planner unit tests include
48 executed original Jinja projection/decision comparisons with synthetic values,
unrounded20-percent boundary, signed grid/DST/units, gap/tail/freshness and PV
learning boundaries. Captured code-only templates have provenance records.

The35-row PARITY-FINAL.md maps every foundation criterion and every live contract
section to concrete implementation and executed test nodes; the reconciliation
script verifies all listed test nodes exist in final JUnit. Documentation-only,
not-executed and commissioning boundaries are explicitly marked, not counted as
blanket full release approval.

## Reproduce

From repository root, use the supplied locked Python environment or create one
exactly as ../foundation/DEVELOPMENT.md and VALIDATION.md describe:

    "$TEST_PYTHON" tools/run_tests.py --junitxml=pytest-results.xml
    "$TEST_PYTHON" tools/run_tests.py tests/packaging -q
    "$LINT_PYTHON" -m ruff check .
    "$LINT_PYTHON" -m ruff format --check .
    git diff --check

Official hassfest source: Core2026.10.1 commit
abe1fdd7cd6b4de1715c87b6fd87d92699514ef9, isolated runner dependencies and command
in VALIDATION.md. No skipped validator/ignored check. The full HACS action cannot
be honestly replaced by the offline7 packaging tests or guessed GitHub responses.
Future authorized publication must run the real HACS workflow and preserve its
check URL, exact commit, resolved image digest and log.

## Safety and privacy evidence boundaries

Safety journal saves finish before commands, and readback must be strictly newer
than latest intent/restore-start boundaries. Partial ACK is not recovery. A failed
save/cancel does not fabricate memory success. Original reserves persist across
five recreated crash states; only pending targets retry after30s. Full marker is
saved independently before restoration; failed marker save blocks commands. Stop,
master-off and close revoke active authorization even if safety persistence fails.
Shadow is absolute and never restores: pending restart requires explicit exclusive
recovery outside shadow, after which mode returns to shadow. FAILED_UNLOAD is not
reported as successful unload; after explicit recovery this pinned HA version may
require restart. No automatic shadow-to-active transition is implemented.

Private release audit checks current candidate files and every unique history blob
against1587 known inventory entity identifiers, the recorded home URL,2185
serial/device/secret-shaped candidates plus generic JWT/private-key/GitHub-token,
private IPv4, home URL, secret-path and private artifact patterns. Current-tree
matches0; eight source/checksum-ledger entries unchanged. Exact file/blob counts,
scan scope and final archive results are in the private task handoff. It is not a
mathematical proof of absence of every possible secret. No actual diagnostics,
backups, private snapshots or household time-series were copied into the candidate.

Two inherited README revisions still contain a private identifier: the inherited
Git history is NOT PUBLISHABLE. No history rewrite was performed during shared
work. The local source archive excludes Git history but does not waive source-rights
review or authorize publication. No git remote/push, GitHub publication, productive
HA call, dashboard change, device command or direct storage-file mutation occurred.

## Explicit remaining limitations and external gates

1. Full official HACS action not executable here; custom-repository/public release
   checks and transitive mutable container images remain open.
2. Do not push inherited Git history. Create a separately reviewed clean publishable
   history only under explicit authorization; retain private original evidence.
3. Legacy source repositories lack a clear root license; inherited MIT does not
   establish rights to every reused template. Owner/source-rights review is required.
4. Required household net-meter Recorder sufficiency, units and historical-profile
   transition still need read-only commissioning. Never substitute the old meter,
   merge histories or invent household measurements to pass parity.
5. Physical cloud/device delivery and third-party state/readback fidelity are not
   established by synthetic transport. Activation needs supervised explicit approval.
6. Existing custom card is not a working native JS adapter. Contract option is an
   explicit non-destructive separate-update specification; retain the old dashboard
   and use native HA cards until that separately tested adaptation is authorized.
7. Diagnostics handler tested in five states; authenticated HTTP/UI export wrapper,
   real dashboard/browser flows and future HA versions are not locally certified.
8. Process cancellation/recreated Store snapshots are crash probes, not filesystem
   power-loss durability tests. Arbitrary unknown external reserve writers cannot
   be proven absent by a configured-automation interlock.

These are preserved release/commissioning gates, not reasons to silently weaken
safety or claim local test success equals a deployed release. Independent review
is downstream; no same-card duplicate review request is made.
