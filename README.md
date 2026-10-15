# EcoFlow Smart Charge

Native Home Assistant orchestration of three batteries through entities supplied by an existing EcoFlow integration. No new EcoFlow cloud connection, account or credentials. Domain: `ecoflow_smart_charge`.

## Status / Entwicklungsstand

Locally integrated and tested candidate, not an approved live controller. The [final integration report](docs/release/INTEGRATION-REPORT.md) and [35-row evidence matrix](docs/release/PARITY-FINAL.md) retain the historical validation evidence. The owner has confirmed redistribution rights and created the public target repository. Earlier HACS attempts first failed at repository lookup and subsequently identified missing repository metadata and a misplaced brand icon; the remediation adds the integration-local icon and binds HACS validation to the exact CI SHA. Current remote results are recorded separately from those historical attempts. Shadow-only deployment is authorized; independent physical commissioning and active cutover are NOT authorized or verified.

Implementierungskandidat, keine freigegebene Produktivversion. Shadow ist der verpflichtende Standard. Ein grüner Packaging-Test ist keine Freigabe zum Laden. Migration, Import, Kartenanpassung und Recovery müssen mit dem fertig integrierten Code nachgewiesen sein. Fehlende Import-/Vergleichsfunktionen sind eine Cutover-Sperre, kein Anlass für manuelle Speicheränderungen.

## Model / Planungsmodell

- Read only the selected mandated net grid-energy meter. Never substitute an EcoFlow or tariff consumption counter or merge histories from different meters.
- Reconstruct hourly household load as grid net energy + measured PV − three battery charge energies + three battery discharge energies. Use the last 14 completed local days, exclude today, normalize Wh/kWh and require at least three valid observations in each local hour; DST is elapsed-time aware.
- Distribute published solar forecasts by the historical PV profile. Learn a correction from up to 14 valid completed-day actual/forecast ratios, without overwriting unevaluated probes on restart.
- Use only actually published quarter-hour prices for the selected tariff. Price gaps, stale inputs, unavailable devices, missing protection modes and an inactive best-price window block charging.
- Compare the unrounded advantage `(avoided_price - current_price) / avoided_price * 100`. The default for NEW installations is 20%; migration preserves existing settings. Efficiency, wear, weighted future consumption and known price coverage affect projected net saving. These are model estimates, not guaranteed savings.
- Save all three original individual reserves before commands, serialize the sole writer and require independent device readback. A service acknowledgement is not restoration. Keep pending recovery and the solar-day full-charge marker across restart.

These are required behavior contracts. See the final integration report for executed product tests, not this feature list alone.

## Safety / Sicherheit

Shadow must send zero hardware calls, including restore, restart, unload, buttons and timers. A pending session in shadow stays pending. Restoration requires explicitly authorized exclusive recovery OUTSIDE shadow, then returns to shadow. Never enable old and new writers simultaneously. Unknown conflict state blocks writes. The integration must not change operating mode to obtain permission to charge.

Shadow darf auch keine Reserve zurückstellen. Vor Legacy-Reaktivierung müssen die ursprünglichen Einzelreserven unter exklusiver Freigabe außerhalb von Shadow wiederhergestellt und frisch zurückgelesen sein. Bei unklarer Zuordnung oder fehlenden Originalwerten: beide Regler gesperrt lassen, nicht raten.

## Requirements and future installation

Declared/test-target minimum: Home Assistant 2026.10.1; development Python 3.14.7 (HA requires >=3.14.2). Recorder history, published tariff prices, PV forecasts, best-price window, sun state and three complete battery bindings are required. Source units, history coverage and service capabilities must be validated. No private entity IDs are public defaults.

Only AFTER a separately approved, validated public GitHub release:

1. In HACS, open Custom repositories, add `mischiminator/ha-ecoflow-smart-charge`, category Integration, and download it. This is not a claim of default-catalog inclusion.
2. Restart Home Assistant, then Settings → Devices & services → Add integration → EcoFlow Smart Charge.
3. Select existing sources and all battery lists in identical slot order. Leave shadow enabled. Do not call cutover or recovery actions merely to test installation.
4. Follow [Migration und Rollback (Deutsch)](docs/migration/MIGRATION-DE.md) or the [English runbook](docs/migration/MIGRATION-EN.md). Import existing settings only through the final validated integration-owned importer; never edit HA storage files.

The target repository now exists. HACS installation and hardware activation have not been verified by this remediation; neither a public source branch nor a successful validator run is installation or commissioning acceptance.

## Operation and dashboard

All native controls/actions must route through the same runtime guard. Action names are `recalculate`, `record_shadow_comparison`, `request_cutover`, `confirm_recovery` and `import_state`; every action requires `config_entry_id`. Cutover and recovery also require intentional `confirmed: true`; cutover additionally requires `commissioning_confirmed: true` attesting separately authorized independent commissioning (not an automatically verified legacy comparison); import defaults to preview with `apply: false`. See [ACTIONS-IMPORT.md](docs/migration/ACTIONS-IMPORT.md) for the current validated schema and a synthetic inactive import example. Use the integration's action selector, not a copied private entry identifier. Recalculate is non-writing in shadow; it must not be described as unconditionally non-writing in active mode. The schemas, English/German descriptions and harness tests are aligned with this explicit external commissioning boundary.

The existing price-charge card is NOT compatible through entity mapping alone. Its legacy master validation and helper service calls require the explicit opt-in update described in [CARD-COMPATIBILITY.md](docs/migration/CARD-COMPATIBILITY.md). Until that update is implemented and tested, use native HA entity cards; retain the old dashboard unchanged for rollback.

## Local checks

    uv venv --python 3.14.7 .venv
    uv pip sync --python .venv/bin/python --require-hashes requirements-test.lock
    uv pip install --python .venv/bin/python -r requirements-lint.txt
    .venv/bin/python tools/run_tests.py
    .venv/bin/python -m ruff check .
    .venv/bin/python -m ruff format --check .

The test runner disables IP sockets (local Unix sockets are allowed for HA). HA/plugin dependencies are exactly pinned with hashes. See [VALIDATION.md](docs/release/VALIDATION.md) for official hassfest/HACS commands, tool provenance and limitations; [PACKAGING-REPORT.md](docs/release/PACKAGING-REPORT.md) records this lane's evidence. CI is validation-only and never deploys, publishes or exercises hardware.

## Privacy, provenance and release gates

Do not commit snapshots, backups, real entity mappings, household histories, tokens, serials, Home Assistant URLs or diagnostic exports. Review diagnostics before sharing. [Diagnostics requirements](docs/release/DIAGNOSTICS.md), [license provenance](docs/release/PROVENANCE.md) and [release checklist](docs/release/RELEASE-CHECKLIST.md) are mandatory gates. The local Git history was sanitized on 2026-10-15: private meter identifiers, household migration values and a machine-specific test path were removed from the two affected historical README versions while preserving every commit and all open worktree changes. All local Git objects were scanned against the private inventory and token/key/URL/IP/path patterns with no matches. GitHub main was subsequently replaced with the sanitized history under explicit authorization and verified through a fresh clone. The operator reports contacting GitHub Support for retained old objects/cached views and has closed the history-cleanup task while explicitly waiving further purge verification; server-side deletion is not independently confirmed. Do not merge pre-rewrite history back into this repository. See the [history repair report](docs/release/HISTORY-PRIVACY.md) for scope and verification, and the [blocker report](docs/release/BLOCKER-REMEDIATION.md) for earlier findings. Publication still requires final-tree/archive privacy review and remote validation.

MIT for this repository's original work; see LICENSE and the provenance gate for any reused sources. No affiliation with or endorsement by EcoFlow, Tibber, Home Assistant or HACS is implied.
