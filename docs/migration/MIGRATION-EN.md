# Migration and rollback (English)

This is the required operating procedure for a future accepted release, not permission to deploy this development candidate. The [German runbook](MIGRATION-DE.md) gives additional detail. If a validated importer, comparison record, exclusive recovery path or matching UI is absent, STOP. Do not replace missing features with storage edits or unsupported calls.

## Preparation

1. Create a supported HA full backup and verify its recovery route. Separately export the four legacy price-charge automation configurations, current settings, learning/session state, both card instances and resource version using supported UI/API. An API snapshot is not a full backup. Verify completeness/checksums; keep this evidence private, outside Git.
2. Identify the planner, reserve controller, daily PV probe and PV learner individually. Identify actual command writers from their contents. Do not disable unrelated EcoFlow connectivity watchdogs.
3. Record all existing economic settings, master state and per-battery capacity. Migration preserves the actual chosen advantage threshold and charge ceiling; 20% is ONLY a new-install default, not an import fallback.
4. Record each battery slot's original reserve, SOC, reserve number, operating-mode select, Self-powered switch and charge/discharge statistics. Maintain identical order in every list. A temporary 100% reserve is never a replacement for a saved original reserve.
5. Capture the complete learning state (up to 14 valid ratios, correction, probe date/energy, evaluated date) and independent solar-day full marker. Never overwrite an unevaluated probe on restart.

## Shadow and source transition

Leave legacy in charge while configuring native shadow. Shadow must send zero hardware services on every route, including restore/recovery, restart, timer and unload. Do not raise reserves or force a charge cycle for testing.

Choose the operator-mandated net grid-energy source, not the different historical legacy source. Verify its Recorder statistic ID, signed net semantics, Wh/kWh units, resets and coverage. Never combine old/new meter histories, invent measurements or silently choose another counter. The last 14 completed local days must provide at least three valid observations for every local-hour bucket. Today is excluded; repeated/missing DST hours follow actual elapsed time. Reconstruct load from the selected grid source + PV − three charge energies + three discharge energies.

Verify the explicitly selected tariff/home's published today/tomorrow quarter-hour series and matching current price; no unpublished future prices. Verify the best-price window, remaining-today/full-tomorrow PV forecasts, sun state and all three protection modes. Do not change operating modes to obtain permission.

## Supported import

Use only the final documented, versioned integration-owned import flow/action in `docs/adapter/ENTITY-SERVICE-CONTRACT.md`. The current adapter exposes `import_state` with `payload` and `apply:false` by default; [ACTIONS-IMPORT.md](ACTIONS-IMPORT.md) documents the checked schema and a purely synthetic inactive example. Final integration acceptance is still required. Raw HA Store/backup documents are not import payloads.

- Preview first in shadow. Verify schema version, source mapping, slot order, finite numeric values, ranges and dates. Missing originals, duplicate targets, booleans used as numbers and malformed learning state must fail without writes.
- Compare every proposed value with the private handover; defaults must not overwrite existing settings. Do not replace an existing native session. Marker and session are separate persistent fields.
- Prefer allowing a live legacy session to finish under legacy's exclusive ownership, with all original reserves read back, before transferring an inactive state. If that is impossible, a separately authorized transfer of the full saved original values and mappings is required with both charging paths locked. Never import a partial session and guess its originals.
- Confirm only the validated preview; importer must save integration-owned state through supported HA APIs, never command hardware. Verify settings, ratios/probe/learn dates, full marker and session status after reload through supported UI/readback.
- A pending imported session remains blocked in shadow. Explicit exclusive recovery outside shadow is required before cutover. Never directly edit `.storage`, RestoreEntity data or another integration's entries.

## Comparison and cutover

Keep a private comparison record over multiple real price/PV cycles: timestamps and freshness, profile validity, selected solar day, full-charge demand, solar surplus, avoided reference price, unrounded advantage, net saving, permission and reason. Cover window transitions, unpublished tomorrow, missing data and restart; exercise synthetic boundary/crash cases in tests, not hardware. Document decision changes caused by the correct new grid meter separately; identical output alone is not parity evidence.

Prove zero native hardware calls with service instrumentation/traces, not merely unchanged reserve values. The comparison must identify its configuration; configuration/mapping changes invalidate approval.

All cutover conditions must hold together:

- Full code/parity acceptance including real HA Recorder/DST, shadow, import, crash and readback tests; explicit operator approval for a supervised window; fresh private backups.
- Fresh valid sources, genuine published prices, sufficient history and three correct protection modes. No pending/corrupt session; every individual original reserve freshly confirmed against its correct mapping.
- Disable ONLY the approved identified legacy price-charge command writers through supported UI/API. Read every writer back as OFF; missing/unknown/unavailable is not OFF. New integration must not automatically turn off foreign entities.
- Deliberately retire or separate PV probe/learning writers to prevent duplicate ownership. Leave unrelated watchdogs unchanged. Check for additional third-party writers: software cannot prove their absence. Recheck configured conflicts before EVERY hardware write.

Only then request `request_cutover` for exactly the intended config entry through the final HA action UI. Reading the resulting mode/reason is mandatory; service success is not activation success. Supervise the first naturally eligible operation; never force eligibility. Any partial failure or unconfirmed readback stops new starts and retains recovery state.

## Stop, recovery, rollback

1. Block new native charge starts. Keep journals/original values; do not immediately delete the entry, uninstall HACS or enable legacy.
2. Under active exclusive ownership use the supported stop/master-off path so it restores original reserves. If already in shadow, shadow itself CANNOT restore. Explicitly authorize exclusive recovery OUTSIDE shadow for the pending journal.
3. Recheck legacy writers OFF and saved target mapping. Price/window/economic failure blocks charging, not restoration of known safe originals; exclusive ownership is still mandatory. Never change device mode to restore.
4. Target `confirm_recovery` to the correct entry, following the final confirmation UI/schema. A service ACK/HTTP success is not readback. Independently verify a fresh reserve report on ALL three devices matching their individual originals. Retry only unconfirmed devices; never recapture originals from temporary 100% values.
5. An offline device, stale report, timeout, corrupt journal or changed mapping keeps recovery pending/blocked and BOTH charging writers off. Do not manually set restored or delete the journal. If the integration cannot operate, the operator must use a supported HA backup/recovery route or supervised original device-entity controls with both controllers disabled and known original values, then independently confirm each readback. Never guess.
6. Only after all restores are confirmed and the journal is inactive, return to shadow and safely stop/unload the native active scheduler/listeners. Failed unload is not success.
7. Restore exact saved legacy configs through supported APIs/UI if necessary. Re-enable only originally enabled legacy price-charge roles with clear ownership; read back their states. Do not blindly enable four automations that were previously off. Restore both changed dashboard cards/resource version if applicable. Remove HACS code only after confirmed safe unload. Keep private evidence/backups.

Restart never silently resumes active charging. Full-charge marker survives session clearing and prevents immediate same-solar-day recharge after slight discharge.

## Dashboard

Entity mapping alone is insufficient. See [CARD-COMPATIBILITY.md](CARD-COMPATIBILITY.md) for the opt-in card update specification. Use native HA standard cards until that separate update is implemented and verified. Keep the old dashboard/resource available for rollback.
