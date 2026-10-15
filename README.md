# EcoFlow Smart Charge

Native Home Assistant custom integration for a **shadow-first** EcoFlow price-charge controller. It orchestrates existing Home Assistant entities from the already-installed EcoFlow integration; it does not create an EcoFlow cloud connection and does not collect credentials.

> Safety status: this repository is an implementation candidate, not an installed controller. It was developed without a Home Assistant Core test environment in this workspace. Do not use `active` mode until an HA-Core harness and a supervised, explicitly approved cutover have passed.

## Safety model

- New entries start in `shadow`; no runtime route sends a reserve service call in shadow mode.
- The pure planner rejects stale sources, invalid rows, insufficient history, price gaps, invalid parameters, missing protection mode, price-ceiling, solar-surplus, marker, price-advantage and net-saving failures.
- The required grid source must be selected as the operator-selected net grid-energy meter; no fallback EcoFlow/Tibber counter is implemented.
- A session journal captures the three individual pre-session reserves using HA `Store.async_save` before any real command. Restoration only clears after individual readback; partial failures remain recovery pending.
- Active mode is deliberately not automatically cut over, and the integration never changes EcoFlow operating modes.

## Planning model

The HA-independent core uses the last 14 complete days and rejects any hourly bucket with fewer than three valid samples. Load reconstruction is:

`grid net energy + measured PV - all three battery charge energies + all three battery discharge energies`

PV forecast is distributed by the historic hourly PV profile. A median PV correction keeps at most 14 valid actual/forecast ratios, accepting only 23+ hourly rows and ratios 0..5. Economics use a consumption-weighted future price, total efficiency plus wear cost, and the unrounded price advantage:

`(avoided_price - current_price) / avoided_price * 100`

The public new-install default is 20%. A migration must explicitly import the existing threshold and price ceiling; it must not reset either value.

## Install (future HACS publication)

After a verified public GitHub release, add `mischiminator/ha-ecoflow-smart-charge` in HACS as a **Custom Integration**, install/restart Home Assistant, then configure it under Devices & services. This has not been automatically installed or read back in this development task.

## Migration and rollback

1. Keep legacy automations enabled and configure the integration with the required smart-meter source.
2. Import validated current options and inactive session/learning state through an integration-owned import UX (never `.storage`). Preserve the existing threshold and price ceiling.
3. Run shadow comparisons across recorded price cycles. Document expected differences caused by the mandated source transition; do not fabricate history or substitute a source.
4. Confirm Recorder unit/history availability and profile transition evidence.
5. Take a fresh legacy automation/card backup. With explicit approval only, disable command-capable legacy control writers, then request supervised cutover.
6. If anything fails, return mode to shadow, wait for confirmed individual reserve restoration, re-enable the saved legacy automations, and verify them in HA. Do not claim a restore without readback.

## Development checks

```sh
python3 -m unittest discover -s tests -v
python3 -m json.tool custom_components/ecoflow_smart_charge/manifest.json
```

CI additionally declares Ruff, HACS validation, and Hassfest. A real HA Core-compatible test environment is required for ConfigFlow, setup/unload, platform, service, diagnostics, and Recorder adapter tests.

## Privacy

Do not commit inventory snapshots, backups, Home Assistant URLs, tokens, serials, raw histories, or dashboard exports. Diagnostics deliberately expose only a small mode/status summary.

## Lizenz

MIT. Economic values are projections from recorded and forecast data; they are not a savings guarantee.
