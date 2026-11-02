# Changelog

Releases are created by pushing a `vX.Y.Z` tag; the release workflow checks the tag against
`manifest.json`, `pyproject.toml` and this file and publishes the section below as release notes.

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
