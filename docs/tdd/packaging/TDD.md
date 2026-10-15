# Packaging RED/GREEN evidence

Skill loaded: test-driven-development. Scope: owned packaging/configuration/docs/tests only; no adapter/core Python edits. External full-suite failures are reported, not silently fixed in another lane. Raw logs are private workspace files, not public artifacts.

| Slice | Test node | Observed RED | Minimal GREEN change |
|---|---|---|---|
| PK01 | `tests/packaging/test_release_metadata.py::test_release_metadata_declares_tested_compatibility` | Exit1: HACS homeassistant was missing (`None != 2026.10.1`) | Declare tested HA minimum and Recorder after-dependency; existing version/domain consistency checked |
| PK02 | `tests/packaging/test_localization.py::test_complete_matching_locales_and_service_fields` | Exit1: canonical strings.json absent | Canonical English strings, matching German/English trees and explicit config-entry action selector |
| PK03 | `tests/packaging/test_ci.py::test_ci_pins_actions_and_uses_locked_test_runner` | Exit1: workflow permissions absent | Read-only immutable action refs, exact compatible Python, hashed test lock, offline runner, pinned lint and format commands |
| PK04 | `tests/packaging/test_documentation.py::test_migration_documents_make_safe_recovery_order_explicit` | Exit1: release runbooks missing | Detailed migration/recovery/rollback/card/diagnostics/provenance/validation/release gates |
| PK05 | `tests/packaging/test_documentation.py::test_license_and_brand_assets_present` | Exit1: inherited icon was only1×1 | Original locally generated256×256 battery PNG; inherited MIT notice retained |
| PK06 | `tests/packaging/test_localization.py::test_fields_match_actual_adapter_schema` | Exit1: added adapter source fields absent from locale schema | Actual AST schema alignment for user/reconfigure selectors and all five actions with confirmed/expected/payload/apply fields |
| PK07 | `tests/packaging/test_documentation.py::test_synthetic_import_example_is_accepted_by_real_validator` | Exit1: synthetic inactive envelope absent | Artificial complete v1 JSON; real adapter validate_import accepts it and preserves settings/learning, shadow/off, no pending session |

GREEN was run after each slice: first metadata1/1, then combined2/2, CI combined3/3, docs/assets combined5/5, actual-adapter alignment6/6, final synthetic example7/7. Final packaging suite is the authoritative aggregate, with JUnit/log in the private handoff. Ruff formatting/import cleanup applied only to packaging test files and rechecked.

These are packaging/schema/guide regressions. They do not prove hardware behavior, transactional crash safety, zero-call importer behavior or end-to-end card compatibility. The synthetic example calls the actual pure import validator only; adapter tests must exercise preview/commit through HA. Full source-schema AST assertions intentionally fail if adapter field structures change, requiring final reconciliation instead of silently drifting.

Mid-flight full-tree run:168 passed/6 failed. Failures were outside packaging ownership: standalone-file foundation import assumptions vs split pure modules; old config-flow fixture lacking new sources; four old safety fixtures expecting prior inputs/runtime. Full-tree lint/format likewise showed in-flight/frozen differences. They were handed to integration reconciliation, never mislabeled as green.
