# EcoFlow Smart Charge

Native Home Assistant integration that charges three batteries from the grid when published electricity prices make it worthwhile. It works through entities supplied by an existing EcoFlow integration: no new EcoFlow cloud connection, account or credentials. Domain: `ecoflow_smart_charge`.

## Planning model

- Read only the selected net grid-energy meter; no substitute or merged meter histories.
- Reconstruct hourly household load as grid net energy + measured PV − three battery charge energies + three battery discharge energies. Use the last 14 completed local days, exclude today, normalize Wh/kWh and require at least three valid observations in each local hour; DST is elapsed-time aware.
- Distribute published solar forecasts by the historical PV profile. Learn a correction from up to 14 valid completed-day actual/forecast ratios, without overwriting unevaluated probes on restart.
- Use only actually published quarter-hour prices for the selected tariff. Price gaps, stale inputs, unavailable devices, missing protection modes and an inactive best-price window block charging.
- Compare the unrounded advantage `(avoided_price - current_price) / avoided_price * 100` against the minimum price advantage (default 20%). Efficiency, wear, weighted future consumption and known price coverage affect the projected net saving. These are model estimates, not guaranteed savings.

## Safety

- Before the first command, all three original individual reserves are saved durably. The integration is the sole writer, serializes every command and requires an independent, fresh device readback; a service acknowledgement is not confirmation.
- When charging is no longer allowed (price, window, master switch off, batteries full), the saved reserves are restored and read back. A pending session and the solar-day full-charge marker survive restarts.
- Unknown or stale sources block charging. The integration never changes the battery operating mode to obtain permission to charge.

## Modes and controls

| Control | Purpose |
|---|---|
| **Controller mode** (select) | `shadow`: calculate and display the plan, never send device commands. `active`: control the battery reserves. New entries start in `shadow`; the selected mode is kept across restarts. |
| **Price charging enabled** (switch) | Master permission. Off blocks new charging and restores the saved reserves of a running session. |
| Numbers | Minimum price advantage, charge price ceiling, efficiency, wear cost, minimum net saving, capacity per battery. |
| **Recalculate plan** (button / `ecoflow_smart_charge.recalculate`) | Refresh the sources and evaluate immediately. Requires `config_entry_id`. |

Switching from `active` to `shadow` first restores the reserves of a running session. If a readback is still outstanding, the session stays pending in shadow; switch back to `active` to finish the restoration. The planner runs every quarter hour, a safety check runs every minute, and source state changes trigger a refresh.

## Requirements

Home Assistant 2026.10.1 or newer (Python ≥ 3.14.2). Recorder history, published Tibber tariff prices (`tibber.get_prices`), PV forecasts, a best-price window, the sun entity and three complete battery bindings (SOC, reserve, Self-powered switch, operating mode, charge and discharge energy) are required.

## Installation

1. In HACS, open Custom repositories, add `mischiminator/ha-ecoflow-smart-charge` with category Integration, and download it.
2. Restart Home Assistant, then go to Settings → Devices & services → Add integration → EcoFlow Smart Charge.
3. Select the sources and all battery lists in identical slot order, plus the tariff key.
4. Check the plan in `shadow` mode, then switch **Controller mode** to `active` and turn on **Price charging enabled**.

## Local checks

    uv venv --python 3.14.7 .venv
    uv pip sync --python .venv/bin/python --require-hashes requirements-test.lock
    uv pip install --python .venv/bin/python -r requirements-lint.txt
    .venv/bin/python tools/run_tests.py
    .venv/bin/python -m ruff check .
    .venv/bin/python -m ruff format --check .

The test runner disables IP sockets (local Unix sockets are allowed for HA). CI additionally runs hassfest and the HACS action; it never deploys or exercises hardware.

## Privacy

Do not commit real entity mappings, household histories, tokens, serials, Home Assistant URLs or diagnostic exports. Diagnostics contain only mode, status and recovery state, never entity IDs.

MIT license; see LICENSE. No affiliation with or endorsement by EcoFlow, Tibber, Home Assistant or HACS is implied.
