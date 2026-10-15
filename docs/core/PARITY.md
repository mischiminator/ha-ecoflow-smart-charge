# Executed core parity map

Scope: core-owned portions of foundation/PARITY.md, not acceptance of the HA
adapter, persistence, packaging or installation. Implementation is in
`custom_components/ecoflow_smart_charge/planner/` (abbreviated `planner/` below).
Test paths below are actual pytest nodes, not proposed names. Parameterized
suffixes are visible in `docs/tdd/core/core-tests.xml`.

Final owned run:148 passed,0 failures/errors/skips; IP network sockets disabled,
Unix sockets allowed only for the installed HA pytest plugin's event loop.
`tests/unit/test_isolation.py` also executes an actual `python -S` child importing
the entire planner package with no Home Assistant/site packages.

| Criterion | Core implementation | Executed evidence |
|---|---|---|
| P01 core boundary | core.build_hourly_profile accepts ONLY supplied joined rows; no alternate source lookup | test_profile::test_completed_local_days_signed_grid_and_dst; source identity validation belongs to HA, no household-history parity claimed |
| P02 core boundary | core.build_hourly_profile local14-day interval, strict rows, UTC dedupe | test_profile::test_completed_local_days_signed_grid_and_dst; test_profile::test_invalid_rows_cannot_satisfy_three_sample_minimum; test_profile_boundaries::test_duplicate_instants_and_naive_rows_cannot_fake_history; units/eight-stream join belongs to HA |
| P03 | core.build_hourly_profile | tests/test_planner.py::ProfileTests; test_profile_boundaries::test_inclusive_zero_ten_plausibility_caps; test_profile_boundaries::test_spring_hour_is_absent_not_fabricated; fall DST in test_profile |
| P05 | core._reason current actual quarter, strict quote tolerance, ordering | test_validation::test_current_quote_strict_tolerance; ::test_duplicate_unsorted_and_hourly_series_are_rejected; ::test_off_quarter_time_and_missing_current_slot |
| P06 | forecast.build_curve solar-day/sunset | test_solar::test_next_solar_day_only_below_horizon_after_noon; ::test_before_sunrise_uses_today_and_zero_denominator_forecast_is_invalid; test_validation::test_naive_and_past_sunset_do_not_raise_or_allow |
| P07 | forecast.build_curve 196 slots, remaining first interval, day denominators | test_solar::test_remaining_first_quarter_separate_day_denominators_and_sqrt_surplus; test_policy_boundaries::test_curve_196_elapsed_quarters_across_dst |
| P08 | forecast.build_curve daylight surplus; core.decide start-only gate | test_solar::test_active_session_only_bypasses_solar_start_gate; ::test_future_solar_deficit_consumes_baseline_before_incremental_energy; tests/test_planner.py::PolicyTests::test_active_session_does_not_stop_only_because_solar_can_now_fill |
| P09 | core.decide missing/target and individual baseline | test_economics::test_partial_tail_coverage_sqrt_target_and_individual_reserves; test_policy_boundaries::test_original_reserves_change_weighting_not_missing_energy; ::test_active_session_never_bypasses_safety_gates; battery shape/reserve/bool cases in test_validation |
| P10 | core.decide baseline before incremental solar-adjusted deficit | test_policy_boundaries::test_original_reserves_change_weighting_not_missing_energy; test_solar::test_future_solar_deficit_consumes_baseline_before_incremental_energy |
| P11 | core.decide partial tail vs internal gap, projected demand | test_economics::test_partial_tail_coverage_sqrt_target_and_individual_reserves; test_validation::test_untraversed_gap_does_not_invalidate_fully_covered_target; test_policy_boundaries::test_no_coverage_is_not_full_coverage_and_no_command_is_embedded; tests/test_planner.py::PolicyTests::test_internal_price_gap_fails_closed |
| P12 | core.decide weighted avoided, cost, scaled net | test_economics; test_policy_boundaries::test_net_saving_has_no_epsilon_or_display_rounding; test_live_parity48 executed templates |
| P13 core boundary | core.decide uses supplied threshold/ceiling unchanged | test_configuration_learning::test_imported_nondefault_advantage_and_ceiling_are_not_replaced; test_policy_boundaries::test_configured_threshold_bounds_and_preservation; new-install defaults/import persistence belong to HA |
| P14 | core.decide reference>0, unrounded percentage plus1e-9 | test_policy_boundaries::test_advantage_unrounded_with_only_one_e_minus_nine_tolerance; ::test_zero_negative_charge_prices_accepted_with_positive_reference; ::test_reference_nonpositive_is_not_economic_permission; legacy precision regression in tests/test_planner.py |
| P15 core boundary | core._reason source freshness flag, price age[0,900), future/naive/time/invalid values | test_validation::test_price_source_age_exclusive; ::test_invalid_required_inputs_fail_closed; ::test_nonfinite_derived_projection_is_rejected; SOC/report/planner age and units belong to HA reader |
| P16 core boundary | core._reason protection flag, core.decide price window | test_policy_boundaries::test_active_session_never_bypasses_safety_gates; test_solar::test_active_session_only_bypasses_solar_start_gate; actual three-switch/select aggregation belongs to HA |
| P17 core boundary | learning.capture_probe frozen once/day state and pending-probe preservation | test_learning::test_probe_survives_restart_and_cannot_be_replaced_before_learning; test_configuration_learning::test_zero_forecast_does_not_capture_or_evaluate_ratio; durable save/race handling belongs to HA |
| P18 core boundary | learning.learn_day/helper accepted ratio series, retention/median/evaluated day | test_learning::test_evaluated_days_advance_even_if_ratio_invalid; ::test_zero_median_is_a_real_learned_correction_not_neutral; test_configuration_learning::test_learning_matching_day_no_double_evaluation_and_fourteen_valid_ratios; completed-day actual-row evidence belongs to HA |
| S05 core boundary | core.decide full-marker deny; solar_day diagnostic | test_policy_boundaries::test_full_marker_blocks_small_discharge_then_new_day_can_plan; persist-before-restore/surviving session-clear is HA-owned and not claimed here |

Tests without a path prefix in this table live in `tests/unit/<name>.py`.
Every random parity case executes both captured projection and decision Jinja,
including partial coverage, gaps, unequal originals, evening and DST cases.

## Current cross-lane integration findings

The full repository was also executed during concurrent adapter/package work:
`docs/tdd/core/full-integration-check.log` records13 failures/158 passes at an
intermediate point. A later final integration check records202 passed /1 failed
in `docs/tdd/core/final-integration-check.log`; the sole remaining failure is the
frozen foundation loader described below, not a failed package-isolation test.
This is NOT a green whole-integration acceptance claim.
Adapter-owned mixed fixtures used old hourly prices and omitted the two binding
additive fields; reported to their owner. The frozen foundation isolation test
loads core.py as an unrelated single file without a package, incompatible with
permitted internal module splits. Core's new package-aware no-site test passes;
reconciliation must correct that frozen loader, not add I/O/sys.path hacks to
production code. These are handed to the already existing reconciliation lane.

There are no core contract stubs. Remaining release gates are actual live-source
transition verification, HA I/O, complete per-target crash journal/readback,
listener lifecycle, versioned migration, packaging and sanitized publication
history. Those belong to the pre-existing downstream graph.
