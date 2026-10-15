# Adapter entity/service contract v1

Domain: ecoflow_smart_charge. Entry-targeted services registered in async_setup.
Every service requires config_entry_id. No service selects the first entry.

Services:
- recalculate: config_entry_id only.
- record_shadow_comparison: config_entry_id, expected mapping with required allowed (bool), reason (string), advantage (number or null), net_saving (number), profile_valid (bool). Records only exact matching valid shadow output; no hardware.
- request_cutover: config_entry_id, confirmed (bool, required true at runtime). Requires fresh successful saved comparison, full source validity, three valid reserves, no session, legacy writers all explicitly off. No hardware until subsequent runtime cycle.
- confirm_recovery: config_entry_id, confirmed (bool). Default false/absent fails. Explicit temporary recovery outside shadow, exclusive writer check, then returns shadow; repeat until all fresh readbacks confirm. No economic charging gates for restoration.
- import_state: config_entry_id, payload (mapping), apply (bool, default false). Supports response, returns preview; versioned settings/learning/session/full marker import only, never hardware. Existing sessions cannot be replaced.

Stable entity keys (unique_id = entry_id + '_' + key):
- sensor: status, reason, missing_energy_kwh, solar_surplus_kwh, avoided_price_ct, net_saving_ct, price_advantage_percent, pv_correction, full_marker_day, solar_day, plan_updated, profile_samples, corrected_forecast_kwh.
- binary_sensor: shadow_active, recovery_pending, session_active, sources_valid, writer_locked, permission.
- number: minimum_price_advantage, charge_ceiling_ct, efficiency, wear_cost_ct, minimum_net_saving_ct, capacity_kwh.
- switch: master (off by default). It is an integration permission switch, never a device switch.
- select: mode (shadow only selectable; active readback after explicit cutover service; cannot bypass service).
- button: recalculate. No recovery button that implicitly authorizes writes.

No private defaults. Native entity names use supported HA translation keys and the shipped EN/DE inventories, verified against the real registry for all six platforms during integration reconciliation. Unique IDs remain unchanged; raw state/reason codes are not localized. Sensors with unavailable plan are unknown, never fabricated zero projections.

Config source selections: grid_energy_entity, pv_entity, price_entity, price_window_entity, forecast_today_entity, forecast_remaining_entity, forecast_tomorrow_entity, sun_entity; ordered triples soc_entities/reserve_entities/self_powered_entities/operating_mode_entities/charge_energy_entities/discharge_energy_entities; tariff_key explicit string; legacy_writer_entities explicit nonempty list of automation entities. Slot order must match across every triple. Reconfigure mappings only without a pending journal. Options: master, bounded numbers, mode restricted to shadow; options cannot activate hardware.
