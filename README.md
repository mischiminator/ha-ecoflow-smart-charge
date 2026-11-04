# EcoFlow Smart Charge

A Home Assistant integration that charges EcoFlow STREAM batteries from the grid **only when it pays off** — and only as much as the sun will not fill tomorrow.

- Charges in the best-price window when the saving beats your thresholds.
- Leaves room for the expected PV surplus, so the batteries reach 100 % with the sun, not the grid.
- Works through your existing EcoFlow integration: no extra cloud account, no helpers to create.

Domain: `ecoflow_smart_charge` · MIT license

---

## Requirements

| What | Used for |
|---|---|
| Home Assistant **2026.10.1+** with Recorder | history for the household load profile |
| [EcoFlow Cloud](https://github.com/tolwi/hassio-ecoflow-cloud) (`ecoflow_cloud`) | 1–10 STREAM batteries and the Smart Meter |
| Forecast.Solar | PV forecast today and tomorrow |
| Tibber + [Tibber Prices](https://github.com/jpawlowski/hass.tibber_prices) (`tibber_prices`) | published quarter-hour prices, current price, best-price window |

Every battery must be in **Self-powered** mode for active charging. The integration never changes the operating mode itself.

## Installation

1. **HACS** → Custom repositories → add `mischiminator/ha-ecoflow-smart-charge` (category *Integration*) → download.
2. Restart Home Assistant.
3. **Settings → Devices & services → Add integration → EcoFlow Smart Charge.**
4. Pick:
   - the EcoFlow batteries and the Smart Meter,
   - the Forecast.Solar and Tibber Prices entries,
   - the Tibber home,
   - optionally an existing PV energy sensor (see [PV energy](#pv-energy)).

   Unique candidates are preselected. All entities are found automatically from these devices and entries; renamed entities are followed on reload.

## First steps

1. New entries start in **shadow** mode: the plan is calculated and shown, but no device is ever commanded.
2. Watch the plan on the [dashboard card](#dashboard-card) for a few days.
3. When it looks right: set every battery to **Self-powered**, switch **Controller mode** to `active` and turn on **Price charging enabled**.

### PV energy

| Option | Effect |
|---|---|
| Select an existing PV energy sensor (e.g. a Riemann sum) | Its history is used right away. |
| Leave it empty | The integration creates its own **PV energy** sensor from the batteries' PV power. The load profile needs about three days of history before planning starts. |

## Dashboard card

The card ships with the integration and loads automatically — no resource to add. Pick **EcoFlow Smart Charge** in the card picker, or:

```yaml
type: custom:ecoflow-smart-charge-card
# device_id: only needed with more than one EcoFlow Smart Charge entry
```

It shows status and reason, the charge target, price, solar surplus, net saving, the planned grid charge, the current or next best-price window, the total and per-battery level (tap for history). The gear opens the settings; every change is read back from Home Assistant before it counts as saved. German and English.

## Controls

| Entity | Purpose |
|---|---|
| **Controller mode** (select) | `shadow` plans only · `active` controls the reserves |
| **Price charging enabled** (switch) | Master permission. Off stops new charging and restores the saved reserves. |
| **Recalculate plan** (button) | Plan now (also `ecoflow_smart_charge.recalculate` with `config_entry_id`) |
| Minimum price advantage | default 20 % |
| Charge price ceiling | default 32 ct/kWh |
| Minimum net saving | default 3 ct/kWh |
| Total efficiency | default 0.85 |
| Wear cost | default 2 ct/kWh |
| Fallback capacity | for battery models without a known capacity (default 1.92 kWh) |

Key sensors: **Decision reason**, **Grid charge target**, **Grid charge energy**, **Missing energy**, **Solar surplus**, **Net saving**, **Price advantage**, **PV correction**.

## How it decides

Every quarter hour:

1. **Load profile** – average household load per hour over the last 14 days, from the grid meter, PV and battery energy.
2. **Solar surplus** – the Forecast.Solar forecast, spread over the day by your PV profile and corrected by a learned factor, minus the expected load.
3. **Grid share** – energy missing to 100 % minus the solar surplus. If the sun covers it, nothing is charged.
4. **Charge target** – one shared reserve for all batteries (they sync it), e.g. 74 % instead of 100 %. Capacity per battery comes from the model: STREAM 1.92 kWh, Ultra X 3.84 kWh.
5. **Economics** – charging must happen inside the best-price window, below the price ceiling, with at least the minimum price advantage and net saving against the later grid price it replaces.

While a session runs, the target follows new forecasts (from 2 percentage points). Once the grid share is reached, the reserve is held until the best-price window ends, so the house runs on cheap grid power. Windows at night and around noon both work.

> Example: 3 × 1.92 kWh at 20 %, 2.6 kWh solar surplus expected → 2.0 kWh from the grid → target **55 %**; the sun does the rest.

**Prices:** only published prices count. Tomorrow's prices appear around 13:00; until then a window is judged on today's remaining prices.

**PV learning:** each day's forecast is compared with the measured PV energy; the median of up to 14 ratios corrects future forecasts (after three days).

## Safety

- **Original reserves first.** They are saved durably before any command and restored when charging ends.
- **Never below your own value.** A reserve is never set below what you had configured.
- **Confirmed by the devices.** Only the system master (the battery with a *Power Sys Load* above 0) is commanded; the slaves' reports of the synced value confirm it. A service acknowledgement is not enough.
- **Fails closed.** Stale or unknown data, a missing Self-powered mode (active only), the master switch or the end of the window stop charging and restore the reserves.
- **Survives restarts.** A running session, its target and the "full today" marker are kept.
- **Shadow is harmless.** It never sends device commands; switching to shadow first restores a running session.

## Troubleshooting

The **Decision reason** sensor says why the integration charges or not. When a source blocks planning, its `detail` attribute names it (e.g. `source_stale: sensor.…`), and the card shows it.

| Reason | Meaning |
|---|---|
| `eligible` | Charging allowed |
| `target_reached` | Grid share charged; reserve held until the window ends |
| `outside_best_price_window` | Waiting for the next best-price window |
| `solar_surplus_sufficient` | The sun will fill the batteries |
| `price_advantage_too_low` / `net_saving_too_low` | Not worth it at the current price |
| `price_above_ceiling` | Price above your ceiling |
| `batteries_full` / `already_full_for_solar_day` | Nothing to do |
| `protection_mode_required` | Active mode needs every battery in Self-powered mode |
| `profile_invalid` | Not enough history yet (3 values per hour) |
| `source_missing` | A source is unavailable or stale — see `detail` |

Diagnostics contain only mode, status and recovery state, never entity IDs.

---

## Development

```bash
uv venv --python 3.14.7 .venv
uv pip sync --python .venv/bin/python --require-hashes requirements-test.lock
uv pip install --python .venv/bin/python -r requirements-lint.txt
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check . && .venv/bin/python -m ruff format --check .
```

Tests run offline (IP sockets disabled). CI also runs hassfest and the HACS action.

**Releases:** bump `version` in `manifest.json` and `pyproject.toml`, add a `## [X.Y.Z]` section to [CHANGELOG.md](CHANGELOG.md), merge, push tag `vX.Y.Z`. The release workflow validates everything again and publishes the release with `ecoflow_smart_charge.zip`.

**Privacy:** never commit real entity mappings, household histories, tokens, serials, Home Assistant URLs or diagnostic exports.

MIT license, see [LICENSE](LICENSE). Not affiliated with or endorsed by EcoFlow, Tibber, Home Assistant or HACS.
