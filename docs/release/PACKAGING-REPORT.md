# Packaging lane handoff

Task scope: HACS metadata/manifest, CI, English/German strings and service forms, original brand asset, migration/recovery/rollback/card/diagnostics/provenance/release documentation. No core/adapter Python, foundation files or frozen dependency lock changed. Existing MIT LICENSE preserved. No publication, remote configured, HA service, automation toggle, dashboard update or hardware exercise performed.

## Executed evidence

- Packaging suite:7 passed,0 failed; no IP sockets. JUnit and logs in private workspace; exact command below.
- Packaging test Ruff lint and format: pass (four files). `git diff --check`: pass.
- Official hassfest source from Core2026.10.1 commit `abe1fdd7cd6b4de1715c87b6fd87d92699514ef9`: all custom-integration validators executed, Exit0,1 integration/0 invalid. One adapter-owned CONFIG_SCHEMA warning remains; no plugin was skipped. This was a real official source run, not a simulated Docker result.
- Actual adapter schema alignment: AST check compares config user/reconfigure source fields and five service names/field sets against the current Python files. Strings/en identical; de has identical leaf paths. Synthetic inactive import JSON accepted by real `validate_import`, preserving settings/learning.
- Brand placeholder was1×1 and failed RED; original256×256 PNG generated locally, no downloaded/vendor artwork.
- Current-tree inventory identifier/home-URL match scan: zero matching files. Broad private scan used1587 candidate concrete IDs/references and one configured Home URL, excluding generic HA service names from the entity candidate set. All historical tracked blobs also scanned: two inherited README revisions match private material. No history rewrite; DO NOT PUSH existing history. This is a targeted scan, not proof against every possible token/serial/household trace.
- A mid-flight whole-product test run was executed and deliberately reported:168 passed/6 failed. The failures concern old/frozen isolation/flow/safety fixtures versus evolving core/adapter interfaces. Whole-tree Ruff/format also fail on unfinished/frozen files. Only owning lanes/final reconciliation may fix these. Packaging7/7 is NOT product acceptance.
- Full HACS Action NOT executed: no Docker on this host and no authorized public repository publication. Official wrapper inspected; job declared but not run remotely. Offline package checks do not substitute for HACS validation.

## Parity row mapping

| Row | Delivered implementation/evidence | Remaining final gate |
|---|---|---|
| P13 | New-install20% described distinctly from preserved imported settings; ACTIONS-IMPORT.md; real-validator synthetic nondefault import test | Product import/UI persistence and actual migration readback |
| H05 | Explicit schema-matched import form, confirmed recovery/cutover fields, synthetic envelope; detailed preview/apply procedure; DIAGNOSTICS.md requirements | Real HA import zero-command/partial-failure/canary diagnostics tests; allowlist final code review |
| H06 | Complete card semantic key inventory, input_boolean/input_number vs native service constraints, three separately bound batteries, timestamp/unit/reason changes, opt-in/rollback specification | Separate implemented/tested card update; spec is NOT a working patch. Use native standard cards meanwhile |
| D01 | manifest/hacs minimumHA, original brand, retained MIT/provenance gate, matching EN/DE/strings, five actual action schemas; metadata/localization/brand tests | Final entity translation hook and schema alignment; owner review of actual copied-source rights |
| D02 | Hashed152-pin HA/plugin lock reused unchanged; Python3.14.7; pinned Ruff0.17.0; immutable direct action refs; pytest/ruff/format/hassfest/HACS jobs; test_ci.py | Final whole-tree green; full HACS runtime; mutable transitive images documented |
| D03 | DE+EN migration/rollback, exclusive recovery outside shadow, original reserve readback before legacy reactivation, backup/privacy gates; current-tree and historical known-ID scans | Sanitized separately reviewed publishable history and release archive/serial/token audit before publication |

## Key alignment notes

Actual adapter contract is `docs/adapter/ENTITY-SERVICE-CONTRACT.md`.
Actions: recalculate, record_shadow_comparison, request_cutover, confirm_recovery, import_state. All require config_entry_id; cutover/recovery require confirmed bool, comparison expected object, import payload object + apply default false. Descriptions do NOT call recalculate universally non-writing in active mode. English/German names for all current stable entity keys are provided, but the adapter currently assigns explicit English names without translation keys: connect supported translation hooks or clearly retain English entity names during reconciliation; changing unique IDs is not a localization fix.

README and detailed guides distinguish implemented schema from required acceptance behavior. No raw private migration values, IDs, serials, Home URLs or source snapshots were copied into examples. Synthetic example contains no IDs/dates and is intentionally not a migration default. Import never licenses replacing real settings with that example.

## Reproduce

    .venv/bin/python tools/run_tests.py tests/packaging -q
    .venv/bin/python -m ruff check tests/packaging
    .venv/bin/python -m ruff format --check tests/packaging
    git diff --check

Set up the exact environment and official validators as in VALIDATION.md. TDD failed-first details are in `docs/tdd/packaging/TDD.md`. Final reconciliation must run all tests and validators on the final tree, audit diagnostic output, close all parity rows and resolve the recorded warnings/failures. Completion of this packaging lane releases that pre-created integration child; it does not approve installation or active control.
