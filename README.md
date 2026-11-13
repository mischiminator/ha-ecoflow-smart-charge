# EcoFlow Smart Charge

Use cheaper grid electricity when your EcoFlow STREAM batteries are unlikely to get enough solar energy, while allowing for the solar surplus expected later.

EcoFlow Smart Charge combines electricity prices, your household's consumption history and the solar forecast to decide **whether grid charging is expected to be worthwhile, and how much to charge**. It controls the batteries through your existing EcoFlow integration.

- **Solar first:** only plan grid charging for the energy the expected solar surplus cannot cover.
- **Simple settings:** choose between **Save more**, **Balanced** and **Protect battery**, or use Advanced for individual limits.
- **Preview before enabling control:** Shadow mode shows the plan without sending device commands.
- **One installation:** the dashboard card is included; no separate card download or Home Assistant helpers are needed.

Forecast savings are estimates, not measured savings or a guarantee. Actual consumption, solar generation, battery losses and device availability can differ from the assumptions.

## Requirements

Set up these integrations and their required entities before adding EcoFlow Smart Charge:

| Requirement | Purpose |
|---|---|
| Home Assistant **2026.10.1 or newer**, with Recorder | Historical energy statistics for the consumption profile |
| [EcoFlow Cloud](https://github.com/tolwi/hassio-ecoflow-cloud) (`ecoflow_cloud`) | One to ten STREAM batteries and an EcoFlow Smart Meter |
| Forecast.Solar | Today's full-day and remaining solar forecasts, plus tomorrow's forecast |
| Tibber and [Tibber Prices](https://github.com/jpawlowski/hass.tibber_prices) (`tibber_prices`) | Published quarter-hour prices, the current price and the best-price window |

For **Active** control, every selected battery must be in **Self-powered** mode. EcoFlow Smart Charge checks this setting but does not change the batteries' operating mode for you. Shadow mode can preview the plan without Self-powered being enabled.

## Installation

### Home Assistant 2026.11 and newer: Marketplace

[Marketplace](https://www.home-assistant.io/integrations/marketplace/) is built into Home Assistant from **2026.11** and replaces the separate HACS integration. Open **Settings → Marketplace** as an administrator; there is no HACS installation step.

1. Choose **Add from link** and enter `mischiminator/ha-ecoflow-smart-charge`.
2. Complete the GitHub connection if prompted. Custom repositories need this connection.
3. If a content type is requested while adding the repository, choose **Integration**. Open its repository page and select **Install**.
4. Continue to the integration setup when it opens. If it does not open, use **Settings → Devices & services → Add integration → EcoFlow Smart Charge**. Follow any restart request shown by Home Assistant.

Already installed through HACS? Home Assistant transfers existing installations and custom repositories to Marketplace when upgrading to 2026.11. You do not need to reinstall this integration. See the [HACS migration information](https://www.hacs.xyz/docs/marketplace/).

<details>
<summary>Still using a supported Home Assistant 2026.10 installation?</summary>

Use HACS on Home Assistant **2026.10.1–2026.10.x**: add `mischiminator/ha-ecoflow-smart-charge` under **Custom repositories**, choose **Integration**, and download it. Restart Home Assistant, then add **EcoFlow Smart Charge** under **Settings → Devices & services**.

These HACS steps are for 2026.10 only, not for 2026.11 or newer.

</details>

### Select your devices and data sources

During setup, select:

- Your EcoFlow batteries and Smart Meter.
- The Forecast.Solar and Tibber Prices integration entries.
- Your Tibber home.
- Optionally, an existing **PV energy** sensor with historical energy statistics.

Unambiguous choices are suggested automatically. The integration resolves the required entities from your selections; you do not need to enter an entity ID for every battery measurement. To change the selected devices or sources later, use **Reconfigure**. Reconfiguration is blocked while a session or recovery is pending.

### Wait for a usable consumption profile

The planner uses hourly energy statistics from the **previous 14 complete local days**. It needs at least **three valid samples for each hour of the day**, with matching grid, PV, battery charge and battery discharge data.

If you select an existing PV energy sensor, suitable history can be reused. If you leave the field empty, the integration creates its own **PV energy** sensor from the selected batteries' PV power. That sensor needs to build history first. Around three complete days can be enough with uninterrupted, valid data; missing statistics can make this take longer.

The card reports whether the profile is **still learning** or **ready**. A value such as `3/14` is the minimum sample count across the hourly buckets within the history window — not a percentage or a forecast accuracy score.

## First use

New setups start with:

- **Settings mode: Simple** and **Charging policy: Balanced**.
- **Controller mode: Shadow**.
- **Price charging enabled: Off**.

Add the [dashboard card](#dashboard-card), let the profile become ready, and review the proposed targets before enabling control. When you are ready, set all batteries to **Self-powered**, select **Active** controller mode, and turn on **Price charging enabled**.

These are separate choices: **Simple / Advanced** controls how you configure the planner; **Shadow / Active** controls whether the integration may send device commands. Choosing a charging policy does not enable grid charging by itself.

## Settings

Open the gear in the card, or go to **Settings → Devices & services → EcoFlow Smart Charge → Configure**. The integration's Configure dialog first asks for Simple or Advanced, then shows the relevant settings. Settings changes are applied to the running controller without reloading the integration.

### Simple

Choose the behavior you prefer, without entering percentage or price-difference thresholds:

| Charging policy | German label | When it considers grid charging |
|---|---|---|
| **Save more** | Mehr sparen | Even for a small expected saving |
| **Balanced** — default | Ausgewogen | When a clear expected saving remains after estimated losses and battery wear |
| **Protect battery** | Akku schonen | Only for a larger expected saving |

All three still use the solar forecast, price ceiling, efficiency and wear assumptions. Simple hides the numerical inputs; it does not disable these checks. The policy names describe how readily the planner charges, not a guaranteed saving or battery lifespan.

### Advanced

Advanced exposes the individual limits and model assumptions:

| Setting | Default | Meaning |
|---|---|---|
| Minimum price advantage | 20% | Required price difference from the later, consumption-weighted grid price |
| Charge price ceiling | 32 ct/kWh | Highest current electricity price that permits grid charging |
| Minimum net saving | 3 ct/kWh | Minimum forecast net benefit after the planner's loss, wear and coverage adjustments |
| Total efficiency | 85% (`0.85` in native settings) | Assumed efficiency from grid through the battery to the household |
| Wear cost | 2 ct/kWh | Assumed battery wear cost per delivered kWh |
| Fallback capacity | 1.92 kWh | Capacity per battery when its model is not recognized |

Simple uses preset net-benefit thresholds of **1, 3 and 6 ct/kWh** for Save more, Balanced and Protect battery, and no additional percentage threshold. These are planning rules, not measurements. The benefit is reduced when the published price outlook only covers part of the planned energy use.

Switching to Simple **does not overwrite your saved Advanced values**. Switching back restores them. Setups created before Simple mode was introduced keep their previous limits in Advanced until you choose otherwise.

The integration's number entities show the saved numerical settings. Editing either economic threshold directly switches to Advanced so the change takes effect; editing a price ceiling, efficiency, wear or capacity value does not switch the mode.

### Everyday controls

| Control | What it does |
|---|---|
| **Controller mode** | Shadow previews the plan; Active can control battery reserves |
| **Price charging enabled** | Allows new charging sessions; turning it off requests restoration of a running session's saved reserves |
| **Recalculate plan** | Requests a fresh evaluation immediately |

Automations can also call `ecoflow_smart_charge.recalculate` with `config_entry_id` to target an integration entry.

## Dashboard card

The card is bundled with the integration and registered automatically when the Home Assistant frontend is available. There is no separate dashboard resource to add. Select **EcoFlow Smart Charge** in the card picker, or use:

```yaml
type: custom:ecoflow-smart-charge-card
# device_id: only needed when more than one EcoFlow Smart Charge entry is configured
```

The card supports German and English and shows:

- Controller status, decision reason and grid-charge target.
- Current price, predicted solar surplus, forecast net benefit and planned grid-charge energy.
- The current or earliest upcoming best-price window.
- A capacity-weighted total battery level and individual battery levels and reserves.
- Consumption-profile readiness and the learned PV correction.

Tap an individual battery tile or the current-price tile for its Home Assistant history. The total battery level is a summary, not a history button. The gear opens the integration settings, not just the card's appearance settings.

## How charging is planned

1. **Estimate household demand.** Average the available hourly energy statistics across the recent history window.
2. **Estimate useful solar energy.** Distribute the solar forecast using the historical PV pattern, apply the learned correction, then subtract expected household use and account for charging losses.
3. **Find the grid share.** Subtract that expected solar contribution from the energy missing to a full battery. No additional grid charge is planned if solar is expected to cover it.
4. **Set a shared target.** Choose a whole-percentage reserve target across the selected batteries. Recognized STREAM models use 1.92 kWh; STREAM Ultra X uses 3.84 kWh. Unknown models use the configured fallback.
5. **Check whether it is worth charging now.** Require the best-price window, the price ceiling and the selected benefit thresholds. Compare charging costs with later grid purchases that the additional stored energy is expected to replace.

The solar period is **not always tomorrow**: before sunset it is the remaining solar opportunity today; after the afternoon sunset it is tomorrow. Both nighttime and daytime best-price windows can be used.

During a session, target changes of at least **two percentage points** are followed, without lowering a battery below its original reserve. Once the grid share is covered, the target is held until the best-price window ends, provided the safety and economic conditions remain satisfied. The integration then requests restoration of the saved reserves.

Evaluation runs on the minute safety timer, quarter-hour schedule and selected source changes. The full Tibber price series is fetched at most once per hour during normal successful operation. Only published prices are used: tomorrow's prices are considered when available, not at a guaranteed publication time.

**PV correction:** eligible daily forecast/measurement comparisons are collected over time. After three accepted comparisons, the median of up to 14 ratios adjusts later forecasts. Until then, the factor is `1.0`. A day needs sufficient hourly PV statistics to contribute; this is separate from consumption-profile readiness.

## Safety and recovery

- **Save before writing.** Original reserves and command intent are stored before device commands are sent.
- **Respect original reserves.** Charge targets are never below the reserves saved at the start of the session.
- **Check device reports.** A service acknowledgement alone does not confirm a change. When fresh system-load readings identify exactly one master, only that battery receives reserve commands and the other batteries' reports confirm synchronization. With one battery, it confirms itself; without a unique master, batteries are commanded and confirmed individually.
- **Stop on invalid conditions.** Missing, invalid or stale required data, loss of Self-powered mode in Active, disabling price charging, or the end of the price window blocks further charging and triggers restoration where a session exists.
- **Keep recovery state.** Sessions and pending restoration survive a restart. A damaged journal blocks recovery rather than being discarded.
- **Keep Shadow command-free.** Switching from Active to Shadow first initiates restoration under Active control. Restoration may still be awaiting confirmation when Shadow starts; Shadow itself sends no further commands. Pending recovery remains visible and needs Active control to complete.

A failed unload leaves the runtime in a restricted recovery state. It can finish restoration but will not start another session until Home Assistant restarts. Saving a setting does not bypass this safeguard. Do not delete the session journal to clear a recovery warning.

## Troubleshooting

Start with the **Decision reason** sensor and the explanation in the card. When a source prevents evaluation, the sensor's `detail` attribute identifies the problem, for example `source_stale: sensor.…`.

| Reason or status | What to check |
|---|---|
| `eligible` | The plan permits charging. Device commands still require Active mode and price-charging permission. |
| `outside_best_price_window` | Wait for a best-price window reported by Tibber Prices. |
| `solar_surplus_sufficient` | The forecast solar contribution covers the missing energy; no extra grid charge is planned. |
| `target_reached` | The session is holding its target until the price window ends. |
| `price_advantage_too_low` / `net_saving_too_low` | The price difference does not meet the current benefit rules. |
| `price_above_ceiling` | The current price exceeds the configured ceiling. |
| `batteries_full` / `already_full_for_solar_day` | Batteries are full, or the full-charge marker prevents another charge for this solar period. |
| `protection_mode_required` | Every selected battery must be in Self-powered mode for Active control. |
| `profile_invalid` | Check Recorder statistics and the three-samples-per-hour requirement. |
| `price_gap` / `insufficient_priced_consumption` | Published prices or forecast consumption do not support the planned comparison. |
| `source_missing` | Check `detail` for unavailable, stale or otherwise invalid source data. |
| `recovery_pending` / `recovery_blocked` | A previous session is unresolved. Check device availability and the recovery state before enabling further charging. |

EcoFlow reserve reports are change-driven. An older, otherwise valid reserve report alone does not make planning stale; command confirmation must satisfy the separate readback checks.

The downloadable integration diagnostics contain summary mode, status and recovery information, not raw entity mappings or household histories. State attributes and logs can still contain source entity IDs; review them before sharing.

## Updates

On Home Assistant 2026.11 and newer, repository updates appear under **Settings → Updates** through Marketplace. Keep the GitHub connection available for custom-repository updates. After updating the integration, restart Home Assistant as requested to load the new code. The bundled card is cache-busted automatically; reload the dashboard if it still shows the old interface.

Configuration changes and software updates are different: saving settings does not require a restart, but installing an integration update does.

## Development

```bash
uv venv --python 3.14.7 .venv
uv pip sync --python .venv/bin/python --require-hashes requirements-test.lock
uv pip install --python .venv/bin/python -r requirements-lint.txt
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check .
.venv/bin/python -m ruff format --check .
node --check custom_components/ecoflow_smart_charge/frontend/ecoflow-smart-charge-card.js
```

Tests run offline, with IP sockets disabled. CI also checks integration metadata with hassfest and repository compatibility with the HACS action. The HACS action and `hacs.json` remain part of Marketplace publishing; they are not instructions to install HACS on current Home Assistant versions.

**Releases:** update the version in `manifest.json`, `pyproject.toml` and the release metadata test, add a version section to [CHANGELOG.md](CHANGELOG.md), then merge and push the matching `vX.Y.Z` tag. The release workflow validates the tagged source and publishes `ecoflow_smart_charge.zip`.

**Privacy:** do not commit real entity mappings, household histories, tokens, serial numbers, Home Assistant URLs or diagnostic exports.

Domain: `ecoflow_smart_charge` · [MIT license](LICENSE). This is an independent community integration, not an official EcoFlow, Tibber or Home Assistant product. Marketplace distribution does not mean Home Assistant has audited or endorsed it.
