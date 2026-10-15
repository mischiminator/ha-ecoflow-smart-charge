# Opt-in card compatibility contract (not an implemented card patch)

Source inspection: existing card `setConfig`, `EF_BINDINGS`, `EF_BATTERIES`, `_update`, `_toggle`, `_save`, `_confirmedService`. The source repo and live dashboards remain unchanged. No private defaults from that source are reproduced here.

## Why remapping alone fails

The old card validates the master as `input_boolean.*`, constrains its form selector to that domain, calls `input_boolean.turn_on/turn_off`, and writes settings through `input_number.set_value`. Native integration entities use `switch`/`number` and runtime guards. The battery display iterates a hard-coded three-device array, separately from general binding lookup. Its last-run display expects a legacy `attributes.timestamp`; price-window rendering expects a specific attribute shape. Replacing IDs alone does not fix these behaviors.

## Required separate opt-in implementation

- Preserve legacy mode byte-for-byte in behavior, defaulting existing cards to legacy. Offer an explicit native backend/version option; never auto-detect active control or silently convert a dashboard.
- Validate native master against the actual adapter contract. An `armed` switch is NOT necessarily the master and must not be mapped as one. If the integration has no equivalent master control, show the actual mode and a disabled control with explanation. Never turn a card toggle into implicit `request_cutover` or recovery authorization.
- Resolve native operations from an allowlist: `switch.turn_on/off` for the actual master, `number.set_value` for writable native numbers. All native entity implementations must call the runtime guard. Do not directly control reserve hardware from the card.
- Cutover/recovery are separate explicit operator actions with the correct config-entry target and final confirmation schema. Ordinary display, form save, master on and card render must never invoke them. Use HA-supported action UI if no audited card action exists.
- Make all three battery slots explicit config bindings (SOC and reserve number each). Preserve slot order and original-value semantics. No hard-coded device IDs, serials or inference from display names.
- Update last-run parsing for actual HA timestamp entities, retain legacy timestamp support only in legacy mode. Validate numeric units and unavailable values; do not label a unitless value as ct/kWh or treat missing state as zero.
- Update state/reason presentation for native machine codes and recovery phases. Pending restoration is never shown as recovered or simply idle. Shadow must be unmistakable even when economics permit charging.
- Keep optimistic-concurrency checks for configuration popups. Validate all edits before the first write, block concurrent state changes, surface partial saves explicitly, re-read after every save. A config-setting readback is NOT evidence of physical reserve restoration.

## Complete semantic mapping inventory

These are card semantic keys, NOT promises of currently available entity IDs. Integration reconciliation maps each to the final entity/service contract. Until available, display unavailable/read-only or use native HA cards; never create fictitious helpers to appear compatible.

| Key | Native requirement / validation |
|---|---|
| master (card `entity`) | Actual guarded master switch, or read-only mode if no equivalent |
| session | Charging/session phase, distinct from recovery pending and shadow |
| permission | Planner permission plus explicit actual writer-state indication |
| reason | Stable machine reason code, localized text and unknown fallback |
| price | Current published price, unit converted to ct/kWh exactly once |
| ceiling | Actual configured charge ceiling, writable bounded number if provided |
| efficiency | Explicit fraction vs percent conversion; never 0.85 displayed as 0.85% |
| wear, margin | Wear and minimum net saving, ct/kWh delivered |
| advantageMinimum, advantage | Configured threshold and computed unrounded advantage, displayed % |
| capacity | Per-battery capacity in kWh, writable only if actually supported |
| factor | Persisted learned PV correction; do not overwrite through a fake writable setting |
| need, solar, forecast | Full-charge demand, positive PV surplus, corrected PV forecast, kWh |
| saving, reference | Coverage-adjusted modeled saving and weighted avoided price, ct/kWh |
| samples | Actual profile coverage/sample semantics; do not label per-hour samples as days |
| updated, day | Aware last-plan timestamp and selected solar day, HA local timezone |
| bestprice | Actual published best-price window and validated start/end attributes |
| battery slots 0..2 | Explicit per-slot SOC sensor and selected physical reserve number |

## Acceptance before dashboard change

Browser/card tests must prove legacy config still works, native mapping uses correct domains/services, all settings and three batteries render, stale/missing states fail safely, percentage/price/time units are correct, pending recovery is not success, unavailable fields cannot be saved, and no render/toggle/save/cutover bypass writes hardware in shadow. Verify both dashboard placement types, keyboard dialog behavior, partial-save errors and concurrency handling.

Operator keeps the old resource URL/version and both card configurations in a private backup. Test a separate preview/dashboard copy with native shadow; use native standard cards until this implementation is accepted. Change both actual cards only as a separate approved cutover step. Rollback restores the saved resource and both configurations after safe controller recovery; card restoration itself never authorizes a writer.
