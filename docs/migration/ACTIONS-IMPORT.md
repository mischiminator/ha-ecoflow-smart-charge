# Entry-targeted actions and import v1

Aligned with the adapter's checked-in `ENTITY-SERVICE-CONTRACT.md` and current Python schema. Integration reconciliation must repeat this check after any code change. All examples are synthetic, NOT captured household settings or instructions to activate hardware.

In HA Developer tools → Actions select EcoFlow Smart Charge and exactly the intended loaded integration entry. Never guess or copy someone else's config_entry_id. Schema selectors are shipped in services.yaml and labels/descriptions in English/German strings.

| Action | Additional fields | Required behavior |
|---|---|---|
| `recalculate` | none | Refresh via guarded runtime; shadow is non-writing, active may act only under safety gates |
| `record_shadow_comparison` | `expected` object | Exact fields: allowed boolean, reason string, profile_valid boolean, advantage number or null, net_saving number. Uses unrounded compared values and valid shadow output; never writes hardware |
| `request_cutover` | `confirmed` boolean | Only intentional true can authorize safe cutover after all gates; never disables old writers |
| `confirm_recovery` | `confirmed` boolean | Explicit true authorizes exclusive restoration outside shadow, then returns to shadow. Not a charging bypass; not proof of restored hardware |
| `import_state` | `payload` object, `apply` boolean default false | Supports optional response; false validates/previews only, true commits reviewed state without hardware commands |

## Preview/import workflow

1. Keep the native entry in shadow with no existing session/corrupt journal. Keep the current legacy controller as sole owner until the safe transition. To obtain a preview response, use HA's supported action response UI/API (`return_response` where applicable), not a guessed custom endpoint.
2. Build the complete payload privately from the supported snapshot/legacy-state readout. Top-level keys must be exactly `schema_version`, `settings`, `learning`, `session`, `full_marker_day`; version is1.
3. `settings` must explicitly include master, mode and ALL six economic parameters shown in [inactive-import.json](examples/inactive-import.json). Mode is shadow. Efficiency is a FRACTION, not percent. Copy existing chosen values; the artificial example must never overwrite a migration's settings. A user-approved master change is explicit, not an import default.
4. `learning`: preserve ratios (up to14, values0..5), correction, probe_day/probe_kwh pair, learned_day. Dates use ISO YYYY-MM-DD, missing values null. Preserve any actual unevaluated probe and full marker; do not replace them with the example's empty state. `session:null` is valid ONLY when the legacy session is truly inactive and originals are confirmed.
5. Select `import_state` with the private `payload` and `apply:false`; inspect response fields schema_version, pending_session, ratio_count, settings, full_marker_day, applied:false. Compare every setting, date/marker and ratio count with private evidence. Preview response is itself private.
6. For a pending legacy session, prefer letting it finish safely first. Do not hand-author a session from current 100% values. Any separately authorized active-session transfer must preserve all three originals and exact configured targets; adapter session schema is the authority, not a raw HA Store object. Invalid/mismatched data blocks migration. There is deliberately no casual active-session copy/paste example.
7. Only after review, call the SAME payload with `apply:true`; verify applied:true and supported readback after reload. Applying saves journal/learning/marker before options. If a save/update fails, stop and inspect the retained shadow/recovery state; import is not a multi-file transactional HA backup restore. No commands are allowed and no existing native session can be replaced.
8. Applying invalidates prior comparison approval. Restart/reload remains shadow. Confirm actual values and rerun shadow comparison before any separate approved cutover.

The synthetic JSON is checked with the real `validate_import` function in a packaging test, not fabricated as an API response. It contains no IDs, URLs, serials, credentials, real price traces or dates. It demonstrates shape only, not a recommended battery capacity, tariff or threshold. Actual persistence/readback, invalid imports and zero-device-call guarantees remain adapter tests/final acceptance requirements.

## Human-readable names

Entity name translations are provided for the adapter's stable keys. The current runtime entity class still sets explicit English names; final reconciliation must connect translation keys using supported HA entity APIs or document English-only entity names. Merely shipping JSON does not prove the UI is translated. Never rename unique IDs or reassign targets just to change a label.
