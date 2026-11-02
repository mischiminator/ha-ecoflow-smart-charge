# EcoFlow Smart Charge

Native Home Assistant integration that charges one or more EcoFlow batteries (up to 10) from the grid when published electricity prices make it worthwhile. It works through entities supplied by an existing EcoFlow integration: no new EcoFlow cloud connection, account or credentials. Domain: `ecoflow_smart_charge`.

## Planning model

- Read only the selected net grid-energy meter; no substitute or merged meter histories.
- Reconstruct hourly household load as grid net energy + measured PV − all battery charge energies + all battery discharge energies. Use the last 14 completed local days, exclude today, normalize Wh/kWh and require at least three valid observations in each local hour; DST is elapsed-time aware.
- Battery capacity comes from the EcoFlow device model (STREAM Ultra/Pro/Max/AC/AC Pro 1.92 kWh, Ultra X 3.84 kWh); unknown models use the fallback capacity setting.
- Charge from the grid only what the expected PV surplus of the solar day cannot fill: grid energy = missing energy − PV surplus. The batteries sync one shared backup reserve, so the planner computes a single whole-percent reserve (e.g. 74% instead of 100%) whose grid charge covers that gap; batteries already above it are left to PV. No grid charging when the surplus alone suffices. Because forecasts update every quarter hour, a running session follows the newest target once it moves by at least 2 percentage points. Once the grid share is reached the session holds the reserve at the lowest battery level until the best-price window ends, so the house runs on cheap grid power and the stored energy is kept for later; PV may still charge on top. The best-price window may lie at night or around noon; at noon the remaining PV surplus of the same day is used.
- Distribute published solar forecasts by the historical PV profile. Learn a correction from up to 14 valid completed-day actual/forecast ratios, without overwriting unevaluated probes on restart.
- Use only actually published quarter-hour prices for the selected tariff. Tomorrow's prices appear around 13:00; before that, consumption after midnight earns no saving in the projection (lower coverage, never a price gap), so a late-morning or noon window is judged on today's evening prices. Price gaps, stale inputs, unavailable devices, missing protection modes and an inactive best-price window block charging.
- Compare the unrounded advantage `(avoided_price - current_price) / avoided_price * 100` against the minimum price advantage (default 20%). Efficiency, wear, weighted future consumption and known price coverage affect the projected net saving. These are model estimates, not guaranteed savings.

## Safety

- Before the first command, the original reserve of every battery is saved durably. The integration is the sole writer and serializes every command. The batteries sync one reserve, so only the system master (the battery with a *Power Sys Load* above 0) is commanded; the slaves' fresh reports confirm it. A service acknowledgement is not confirmation. A restore whose value never changed during the session is accepted after a 2-minute sync grace, since EcoFlow reports only changes.
- Reserves are never set below the user's own value. The current target is stored with the session and survives restarts.
- When charging is no longer allowed (window ended, price, master switch off, batteries full), the saved reserves are restored and read back. Only completely full batteries set the solar-day marker; otherwise a later window of the same solar day (e.g. at noon after a night session) may top up again. A pending session and the solar-day full-charge marker survive restarts.
- Unknown or stale sources block charging, as does any battery whose Self-powered operating mode is off in active mode (shadow mode plans without it). The integration never changes the battery operating mode to obtain permission to charge.

## Modes and controls

| Control | Purpose |
|---|---|
| **Controller mode** (select) | `shadow`: calculate and display the plan, never send device commands. `active`: control the battery reserves. New entries start in `shadow`; the selected mode is kept across restarts. |
| **Price charging enabled** (switch) | Master permission. Off blocks new charging and restores the saved reserves of a running session. |
| Numbers | Minimum price advantage, charge price ceiling, efficiency, wear cost, minimum net saving, fallback capacity for unknown models. |
| **Recalculate plan** (button / `ecoflow_smart_charge.recalculate`) | Refresh the sources and evaluate immediately. Requires `config_entry_id`. |

Switching from `active` to `shadow` first restores the reserves of a running session. If a readback is still outstanding, the session stays pending in shadow; switch back to `active` to finish the restoration. The planner runs every quarter hour, a safety check runs every minute, and source state changes trigger a refresh.

## Dashboard card

The integration ships its own Lovelace card and loads it automatically — no resource to add. Add **EcoFlow Smart Charge** from the card picker or use:

```yaml
type: custom:ecoflow-smart-charge-card
# device_id: only needed with more than one EcoFlow Smart Charge entry
```

The card finds the entry's entities through its service device and shows status and reason, the charge target, current price, solar surplus, net saving, planned grid charge, the current or next best-price window, the capacity-weighted total level and every battery with its reserve (tap for history). The gear opens a dialog for the master switch, controller mode and all numbers; every change is read back from Home Assistant before it counts as saved. Texts follow the Home Assistant language (German or English).

## Requirements

Home Assistant 2026.10.1 or newer (Python ≥ 3.14.2) with Recorder and these integrations — no template, `input_*` or other helpers need to be created:

- **EcoFlow Cloud** (`ecoflow_cloud`): one or more Stream batteries (SOC, backup reserve, Self-powered switch, charge/discharge energy, PV power) and the Smart Meter (net grid energy).
- **Forecast.Solar**: PV forecast today, remaining today and tomorrow.
- **Tibber** (`tibber.get_prices`) and **Tibber Prices** (`tibber_prices`): published quarter-hour prices, current price and best-price period.
- The built-in `sun.sun`.

PV energy: select an existing Riemann-sum PV energy sensor to keep its history (a single `integration` sensor with "pv" in its name is suggested). Leave it empty and the integration creates its own **PV energy** sensor, integrating the batteries' PV power once a minute; the load profile then needs at least three days of its history.

## Installation

1. In HACS, open Custom repositories, add `mischiminator/ha-ecoflow-smart-charge` with category Integration, and download it.
2. Restart Home Assistant, then go to Settings → Devices & services → Add integration → EcoFlow Smart Charge.
3. Select the EcoFlow batteries (all found batteries are preselected), the Smart Meter, the Forecast.Solar and Tibber Prices entries, optionally an existing PV energy sensor, and the Tibber home. Unique candidates are preselected; all entities are resolved from the devices and entries, and entity renames are followed on reload.
4. Check the plan in `shadow` mode, then switch **Controller mode** to `active` and turn on **Price charging enabled**.

## Local checks

    uv venv --python 3.14.7 .venv
    uv pip sync --python .venv/bin/python --require-hashes requirements-test.lock
    uv pip install --python .venv/bin/python -r requirements-lint.txt
    .venv/bin/python tools/run_tests.py
    .venv/bin/python -m ruff check .
    .venv/bin/python -m ruff format --check .

The test runner disables IP sockets (local Unix sockets are allowed for HA). CI additionally runs hassfest and the HACS action; it never deploys or exercises hardware.

## Releases

Bump `version` in `custom_components/ecoflow_smart_charge/manifest.json` and `pyproject.toml`, add a `## [X.Y.Z]` section to `CHANGELOG.md`, merge, then push the tag `vX.Y.Z`. The release workflow reruns the full validation, checks tag, versions and changelog, and publishes the GitHub release with that section as notes and `ecoflow_smart_charge.zip` attached. HACS picks the release up automatically.

## Privacy

Do not commit real entity mappings, household histories, tokens, serials, Home Assistant URLs or diagnostic exports. Diagnostics contain only mode, status and recovery state, never entity IDs.

MIT license; see LICENSE. No affiliation with or endorsement by EcoFlow, Tibber, Home Assistant or HACS is implied.
