# Changelog

Releases are created by pushing a `vX.Y.Z` tag; the release workflow checks the tag against
`manifest.json`, `pyproject.toml` and this file and publishes the section below as release notes.

## [1.0.7] - 2026-11-11

### Changed
- The dashboard card now labels the consumption profile as ready from three historical samples per hourly bucket, or still learning below that threshold. The footer includes the minimum sample count against the 14-day history window, for example "Verbrauchsprofil: bereit (3/14)".
- The solar forecast adjustment is now shown as "PV-Korrektur: ×0,92", with matching English text and locale-specific number formatting. Missing or invalid profile counts are shown as unavailable instead of implying readiness.
- Charging decisions, planning thresholds and device controls are unchanged.

## [1.0.6] - 2026-11-04

### Fixed
- A confirmed charging session stays confirmed. EcoFlow reports the reserve only when it changes, so the master was commanded again every minute once the last report was older than 2 minutes; any report after the command now counts.
- PV learning no longer stops for good when a day has too few hourly values (e.g. the integration's own PV sensor created in the afternoon): such a day is closed without a ratio after a week.
- When an entry fails to unload during a session (e.g. options saved while charging), the restore is still confirmed or repeated, and no new session starts until Home Assistant restarts.

### Changed
- Tibber prices are fetched once per hour instead of every minute, and the session journal is only written when it changes.
- Leaner code: duplicated input checks, unread journal fields and test-only code were removed. A missing journal file now means "no session" instead of blocking.
- Texts: one name for the price charging switch ("Price charging enabled" / "Preisladung erlaubt"), the same words for the same settings in card, options and entities, German texts say "Akku" throughout, and the card is titled "EcoFlow Smart Charge" in German too.
- The dashboard card no longer reads every saved value back over the REST API and no longer rejects a save when a value changed elsewhere in the meantime.

## [1.0.5] - 2026-11-02

### Fixed
- The activity log no longer fills with "Plan updated" entries every few seconds. The plan timestamp now shows the planning quarter hour (a timestamp sensor in the diagnostic category), so it changes at most four times an hour.
- Fewer refreshes: only the best-price window, price, Self-powered switches, reserves and the sun trigger an immediate re-plan. Grid, PV and battery meters, SOC and forecasts report every few seconds and are covered by the minute safety check and the quarter-hour plan.

## [1.0.4] - 2026-11-02

### Changed
- Reserve commands go only to the system master — the one battery whose *Power Sys Load* is above 0 — and are confirmed by the slaves, which pick up the synced value and report the change. The master is determined anew for every command; with a single battery it confirms itself, and without a unique master every battery is commanded as before.

### Fixed
- Restoring a reserve that never changed (for example after a charge command that did not reach the devices) no longer waits forever for a report EcoFlow never sends: when every confirming battery still shows its original value and has reported nothing since the session started, the restore counts as confirmed after a 2-minute sync grace. Charging is never confirmed this way.

## [1.0.3] - 2026-11-02

### Fixed
- EcoFlow Cloud reports the backup reserve only when it changes (and on restart), so any age limit kept planning at `source_stale` for hours. Planning now only needs a valid reserve value; commands still need a fresh readback after each write.
- The current price is reported once per quarter hour. Its age limit was exactly 900 s, so the minute safety check could see it stale right at each boundary and end a running session. It is now 20 minutes; the price is still checked against the published quarter-hour series.

## [1.0.2] - 2026-11-02

### Changed
- Shadow mode plans even when the batteries are not in Self-powered mode (e.g. AI mode), since it never commands the devices. Active mode still requires Self-powered on every battery, and switching to active re-checks it before any command.
- The decision reason sensor exposes `self_powered`; in shadow mode the dashboard card notes when active mode would still need it.

## [1.0.1] - 2026-11-02

### Fixed
- Planning no longer stops with `source_missing` when EcoFlow reports the backup reserve only every few minutes: SOC and reserve may be up to 10 minutes old for planning. Commands still require a fresh device readback after each write.

### Added
- When planning is blocked by a source, the decision reason sensor names it in its `detail` attribute (e.g. `source_stale: number.…`), the dashboard card shows it, and the log gets one warning per new cause.

## [1.0.0] - 2026-11-02

First stable release.

### Setup
- Select only the EcoFlow batteries, the EcoFlow Smart Meter, the Forecast.Solar and Tibber Prices entries, optionally an existing PV energy sensor, and the Tibber home. All entities are resolved from the devices and entries; unique candidates are preselected and entity renames are followed on reload.
- No Home Assistant helpers are needed. Without a PV energy sensor the integration creates its own **PV energy** sensor from the batteries' PV power.
- The operating-mode select is gone; every battery's Self-powered switch is the protection gate.

### Planning and control
- One to ten batteries; capacity comes from the device model (STREAM 1.92 kWh, Ultra X 3.84 kWh) with a configurable fallback.
- The grid only charges what the expected PV surplus of the solar day cannot fill, as one shared backup reserve (the batteries sync it).
- Running sessions follow the quarter-hourly forecast once the target moves by at least 2 points, and hold the reserve until the best-price window ends — at night or around noon.
- The solar-day marker is set only when all batteries are full, so a later window of the same solar day may top up.
- New sensors: grid charge energy and grid charge target.

### Dashboard card
- Bundled `custom:ecoflow-smart-charge-card`, loaded automatically: status, charge target, price, solar surplus, net saving, best-price window, total and per-battery levels, and a settings dialog with read-back confirmation. German and English.

### Upgrading from 0.1.0
- Entries created with 0.1.0 keep their entity mapping. Open **Reconfigure** to switch to the device-based selection, model capacities and the automatic entity resolution.

## [0.1.0] - 2026-10-15

Initial public HACS custom-repository release.
