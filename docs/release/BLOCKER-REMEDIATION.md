# Blocker remediation — 2026-10-15

Status: local fixes verified; NOT a release or production cutover approval.
This report supersedes older gate descriptions, not their immutable historical logs.
Baseline: `5b385144ee17b4f2285efbcafb7fafbda275b691`.

## Findings, causes and disposition

| Finding | Cause / reproduction | Disposition / verification |
|---|---|---|
| Native self-comparison treated as commissioning proof | Submit native output as `expected`, then request cutover using only `confirmed:true`. Baseline accepts it; the new regression initially failed because no rejection occurred. | Fixed the authorization boundary using the review's explicit external-gate alternative: separate required `commissioning_confirmed:true`, no automatic claim of independently sourced parity. Missing/false attestation rejects with zero device calls. Actual external commissioning remains OPEN. |
| Plan changed since comparison | A recorded permission could differ from the refreshed plan while still within 20 minutes. | Cutover now compares every stored expected value again; changed values reject. |
| README status/schema inconsistencies | README still described full HACS execution as outstanding despite the documented failed authenticated attempt, referred to a packaging task, and omitted the commissioning boundary. | Corrected current README, EN/DE service metadata, action schema/selectors, migration runbooks and adapter contract. Historical logs remain explicitly historical. |
| Private inherited README history | Two inherited README revisions match private inventory identifiers. A clean working tree does not sanitize Git objects. | Preserve the shared audit repository. Prepare a separate root-commit candidate from the reviewed current files; do not clone/push inherited objects. Verify exact file equality and scan every reachable candidate blob and commit. The audit clone is still NOT publishable. |
| Official HACS/GitHub validation unavailable | Authenticated target repository lookup returns HTTP404. Issues, pull requests, action runs and check-run endpoints cannot be inventoried without the repository. | OPEN, not a test pass or evidence that no issues exist. GitHub changes are authorized by this task, but source-rights clearance is still missing; no public repository or release was created merely to force a passing check. |
| Legacy-source redistribution rights | Existing provenance document records missing upstream LICENSE/NOTICE; behavioral Jinja fixtures and source ancestry need owner clearance. | OPEN. An inherited MIT notice is preserved, but is not treated as authorization for unrelated sources. Ask the owner to confirm rights or identify content requiring replacement before publication. |
| Real meter and device commissioning | Synthetic HA/SQLite/transport tests cannot prove the actual required meter history, individual device delivery/readback or rollback under physical partial failures. | OPEN. No hardware writes or production changes in this task. Require a separately approved commissioning window and retained independent legacy/meter/readback evidence. |

## Executed checks

- Fresh isolated baseline: 235 passed, no failures or skips.
- Actual failed-first regression: 4 failed; the missing-attestation case demonstrated baseline activation without independent commissioning authorization. Additional failures exposed the then-missing new API argument.
- After implementation: 239 passed, including real HA service dispatch rejecting missing/false commissioning attestation before the successful explicitly attested synthetic path.
- Full-tree Ruff 0.17.0 check and format check, `git diff --check`, official immutable Docker hassfest and exact-candidate archive rerun: retain fresh logs in the task evidence bundle. A dependency interpreter without Ruff was not reported as a passing lint run; pinned `uvx` is used instead.
- Prior official HACS container evidence is retained under `evidence/`; current authenticated GitHub endpoint probes are retained with the task. Full HACS acceptance still requires the actual authorized accessible remote SHA.

Reproduce from the candidate root with the locked HA environment:

    /path/to/locked-ha-env/bin/python tools/run_tests.py tests -q
    uvx --from ruff==0.17.0 ruff check .
    uvx --from ruff==0.17.0 ruff format --check .
    git diff --check

Use the exact immutable hassfest command in `DOCKER-VALIDATION.md`. Do not ignore
HACS checks, fabricate remote responses, substitute an unrelated repository, or
publish copied source before its redistribution rights have been confirmed.

## Explicit boundary

`commissioning_confirmed` is a privileged operator attestation, NOT proof that
software has authenticated a legacy/reference measurement. It must only be true
after independently generated same-input comparison, meter history/units/sign/reset
verification, and supervised device/recovery checks have actually passed. A caller
can lie; this integration does not claim to detect that. Copying native output is
not independent evidence. The runtime's source validity, writer exclusion,
reserve freshness, durable journal and independent restoration readback gates are
unchanged. Default/restart/reload behavior remains shadow-only.

## Authorization and remote follow-up

The owner subsequently confirmed source redistribution rights, confirmed the existing
public target repository, and authorized immediate SHADOW-ONLY operation. The rights
and repository-404 rows above describe the earlier investigation, not current gates.
No active commissioning, cutover, recovery writes or disabling legacy writers is
authorized by that shadow-only instruction.

The first accessible remote run at `5b385144ee17b4f2285efbcafb7fafbda275b691`
failed three real HACS content checks: missing repository description, missing topics,
and missing `custom_components/ecoflow_smart_charge/brand/icon.png`. Repository
metadata is now configured and the original icon is copied into that integration-local
path. CI explicitly passes `REPOSITORY_REF: ${{ github.sha }}`: hardcoding the
repository alone otherwise validates its default branch rather than the tested SHA.
Both packaging requirements have failed-first regressions. The comparison regression
suite now also covers exactly 1200 seconds, 1201 seconds and every stored expected
field, with shadow/unauthorized/zero-call assertions (246 tests overall).

The operator requested these patches in the current local worktree;
existing unrelated provenance edits must be preserved. Shadow installation is a
separate operational follow-up. Physical acceptance and active cutover remain open,
not prerequisites for the explicitly authorized non-writing shadow phase.

The newly existing public main branch was populated with the inherited history.
Its historical privacy problem is not repaired by a new clean branch. Do not
force-rewrite or delete main without targeted operator authorization. A separately
rooted candidate avoids adding that old history; it does not erase already served
GitHub objects/caches or establish physical device acceptance. Existing card/browser
changes remain out of scope and must not be advertised as implemented.
