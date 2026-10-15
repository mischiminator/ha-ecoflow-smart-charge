# Adapter parity handoff

This maps adapter-owned rows of ../foundation/PARITY.md to executable boundaries.
Tests are under tests/ha unless otherwise named. Core arithmetic, DST projection,
threshold epsilon and original-template comparisons remain core-lane evidence;
this report does not replace them or assert final release acceptance.

| Rows | Implementation | Executed evidence |
|---|---|---|
| P01/P02/H04 | reader.read_statistics, join_statistics; configured IDs only | test_reader::test_recorder_query_real_populated_sqlite; test_join_has_no_missing_stream_zero_fallback; test_statistics_validation (unknown unit, duplicate rows) |
| P04 | reader.parse_prices, SourceReader.refresh; selected tariff only | test_reader::test_reader_parses_only_selected_published_tariff; test_source_pipeline::test_source_to_plan_selects_tariff_and_fails_closed_on_wrong_home |
| P13 | config_flow.SETTINGS; migration.validate_import; native number | test_import_restart::test_supported_import_preview_apply_and_diagnostics_redaction; test_native::test_real_entities_master_numbers_and_cleanup |
| P15/P16 | reader.fresh/numeric/refresh; runtime per-call gates | test_reader::test_source_freshness_exclusive_and_future; test_native_control::test_native_cutover_conflict_and_verified_restoration; tests/test_safety_regressions.py |
| P17/P18 | SourceReader.learn; journal.async_set_learning; pure capture/learn | test_sampling (fixed local time, missing forecast, incomplete day); test_pv_statistics (real SQLite PV-only query/Wh); test_source_pipeline::test_learning_persists_probe_then_learns_yesterday_before_new_probe |
| S01 | storage.async_capture_before_command/async_intent; Runtime._execute | test_executor::test_save_failure_and_conflict_send_no_commands; test_crash_boundaries::test_cancelled_initial_save_sends_zero_commands; test_journal::test_failed_phase_save_does_not_commit_memory |
| S02/S03 | serialized Runtime._execute, persisted IDs/intent_targets, fresh readback | test_executor (ACK, originals, stale, inter-call conflict, partial failures, rate limit); test_crash_boundaries::test_readback_from_before_latest_command_does_not_confirm; test_native_control (real targeted HA services, strict-after-intent timestamps) |
| S04 | runtime.async_close/async_set_shadow; __init__.async_unload_entry | test_crash_boundaries (cancel/save/readback/stop matrix); test_import_restart::test_restart_pending_shadow_does_not_write_and_failed_unload_keeps_services; test_manager_lifecycle (real options reload and disable) |
| S05 | independent full_marker_day; _restore marker-before-commands | test_crash_boundaries::test_full_marker_is_saved_before_restore_command_and_survives_clear; test_journal::test_marker_survives_session_clear; test_source_pipeline::test_full_soc_is_retained_for_marker_even_if_tariff_fails |
| S06 | absolute Runtime.mode/authorization gate and explicit recovery | test_shadow_recovery::test_pending_shadow_restore_never_calls_hardware; test_import_restart restart/unload; test_native_control shadow comparison/cutover |
| S07 | explicit comparison/cutover, per-call ownership check | test_executor::test_no_cutover_without_confirmation_or_comparison; test_conflict_is_rechecked_between_each_device_write; test_native_control; test_reconfigure_safety |
| S08 | storage.validate_session/load; runtime mapping check | test_journal (unknown version, malformed fields, unchanged disk); test_crash_boundaries::test_restart_of_missing_existing_journal_is_blocked; import schema-version parametrization |
| H01 | ConfigFlow/OptionsFlow, source/unit/triple/duplicate checks | test_native::test_valid_flow_and_options_do_not_allow_active_bypass; test_reconfigure_safety; tests/test_config_flow.py; test_manager_lifecycle |
| H02/H03 | __init__ timer/state/start/stop subscriptions, six platforms, target services | test_native (actual registry, entities, services, cleanup); tests/test_ha_integration.py; test_manager_lifecycle; test_native_control |
| H05 | migration preview/apply; diagnostics summary allowlist | test_import_restart (preserved nondefault settings, shadow, invalid envelope version, no raw selected IDs in diagnostic) |
| H06 | ENTITY-SERVICE-CONTRACT.md and packaging card spec | Documentation-only opt-in adaptation; no source JS/dashboard writes and no claim of working native compatibility without card changes. Native HA entities are operational. |

## Limits to preserve in final reconciliation

- Populated Recorder tests prove selected-stream joins, Wh normalization and
  missing/unknown-unit handling with actual SQLite. Household meter sufficiency
  and profile transition still require separate read-only commissioning; no
  alternate meter may be substituted.
- Transport doubles are intentional: no real reserve was raised, no production
  HA configuration changed. Real HA control-path coverage does not prove cloud
  device delivery or a third-party integration's physical readback fidelity.
- The manager FAILED_UNLOAD state needs restart after explicit recovery in the
  pinned HA version; it is not a successful unload or automatic retry claim.
- Entity labels remain English; translations for flows/services are packaging
  work. Newly exposed solar_day/plan_updated/profile_samples/corrected_forecast_kwh
  and session_active keys are now included in the key inventory for final alignment.
- Frozen foundation standalone core-loader failure belongs to reconciliation.
  Do not patch core relative imports to mask it. Full-package pure isolation tests
  supplied by core pass separately.
- No publication, HACS/full-release acceptance or inherited-history sanitization
  is claimed by this adapter phase.
