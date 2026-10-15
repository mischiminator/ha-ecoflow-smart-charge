# Evidence and precedence

This is a sanitized engineering contract, not a copy of household inventory.
Private source labels below are resolved only in the local foundation handoff,
outside this repository. Never copy raw source JSON or real entity mappings here.

1. C: private migration contract, sections Planning, Session safety, Current values,
   Card compatibility, Cutover and Open blockers. Governs required target behavior.
2. L: exact captured live automation configs; planner actions[4].variables includes
   ctx, profile_raw, projection_raw, decision_raw. Controller actions capture and
   restore reserves. Learner/sample actions and triggers govern daily learning.
3. R: complete architecture research handoff, findings.architecture_contract,
   tests, packaging_ci, sources and constraints_risks; not the truncated summary.
4. H: real pinned HA harness environment and lock, setup/unload and SQLite probe.
5. G: legacy README, PRICE-ADVANTAGE.md, build_config.py, bundle.json,
   planner-with-price-advantage.json and permission-with-price-advantage.jinja.
   Historical explanatory sources only, NOT an installer or authority over L.
6. K: existing card JavaScript EF_BINDINGS, setConfig and service handlers.

No missing ARCHITECTURE.md has been invented: R exists as structured task-run
metadata. C/L/R/H were read before this contract. The private handoff records
absolute paths, provenance and hashes; operators retain that ledger locally.

## Public primary references

Research R supplies these sources. Lifecycle, options and HACS integration pages
were also opened during foundation work. APIs used by code must pass the pinned
HA harness; live documentation may describe a later Core than the test target.

- https://developers.home-assistant.io/docs/config_entries_index/
- https://developers.home-assistant.io/docs/core/integration/config_flow/
- https://developers.home-assistant.io/docs/core/integration/options_flow/
- https://developers.home-assistant.io/docs/integration_setup_failures/
- https://developers.home-assistant.io/docs/integration_listen_events/
- https://developers.home-assistant.io/docs/asyncio_blocking_operations/
- https://developers.home-assistant.io/docs/core/integration/diagnostics/
- https://developers.home-assistant.io/docs/dev_101_services/
- https://developers.home-assistant.io/docs/development_testing/
- https://developers.home-assistant.io/docs/creating_integration_manifest/
- https://developers.home-assistant.io/blog/2025/11/25/storage-helper-opt-in-serialize-in-executor/
- https://www.hacs.xyz/docs/publish/start/
- https://www.hacs.xyz/docs/publish/integration/
- https://hacs.xyz/docs/publish/action

## Deliberate distinctions

C requires the selected mandated net meter, NOT the different meter used by L.
Do not mix or fabricate histories to conceal the resulting decision differences.
C strengthens recovery and shadow guarantees beyond the legacy helpers.
L permits partial known consumption coverage: unpublished tail energy contributes
zero saving. G's older full-coverage wording and existing scaffold implementation
are not the parity oracle. Internal gaps still block.
Signed net energy can be negative (export); reject negative reconstructed household
load, PV or charge/discharge magnitudes rather than treating export as bad data.
C's general negative-row wording is interpreted with L's actual balance formula.
The raw helper template configuration was not publicly exposed in inventory:
G's permission template is secondary evidence for timing limits, not claimed live
helper-source readback. Conservative timing gates are explicit target decisions.
