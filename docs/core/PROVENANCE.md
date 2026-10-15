# Core model and provenance

The public facade is `custom_components/ecoflow_smart_charge/planner/core.py`.
All inputs/outputs are frozen dataclasses. `decide` never performs I/O and always
returns `command_plan=()`. The runtime, not the planner, owns device actions,
exclusive-writer checks, readback, master and durable session/marker storage.

## Model

- `build_hourly_profile(rows, now=...)` accepts adapter-joined kWh changes for
  exactly eight statistics streams. Select complete local days in
  `[local midnight - 14 calendar days, local midnight)`, joining/deduplicating
  actual instants in UTC. Signed grid export is valid; reconstructed household
  load is `grid + pv - sum(charges) + sum(discharges)`. Reject invalid rows,
  nonfinite values, booleans, negative charge/discharge and load/PV outside 0..10.
  Each of 24 hour buckets needs >=3 samples; repeated DST hours count separately.
  Omitting `now` exists only for old pure-test callers, never the HA reader.
- `forecast.build_curve` produces exactly 196 elapsed quarter hours, starting at
  the current actual UTC quarter boundary. The first slot uses remaining time.
  PV weights use the local historic hour; separate today/tomorrow denominators
  distribute remaining-today/full-tomorrow forecasts and correction. Later days
  have no fabricated solar forecast. Zero weight with positive forecast blocks.
- Solar day is tomorrow only below horizon at local hour >=12. A future
  `sunset`/next_setting is mandatory. Positive daylight solar minus load is
  multiplied by sqrt(total efficiency). It blocks new starts at >=missing DC
  energy, but this is the ONLY gate an active session can bypass.
- Missing DC capacity is individual per battery. Existing usable AC energy uses
  each ORIGINAL reserve and sqrt(efficiency); current temporary 100% reserve
  readbacks must never be supplied as originals. Future projection starts after
  the current quarter, nets solar against load, consumes baseline before new
  energy, and uses actual published prices only. An internal traversed gap blocks;
  an unpublished tail allows partial useful coverage. No fixed charger watts.
- Avoided reference is weighted price of actually covered incremental demand.
  Target AC = missing DC * sqrt(efficiency). Cost=current/efficiency+wear.
  Saving=(avoided-cost)*min(coverage/target,1), so unpriced tail adds zero saving.
  Advantage=(avoided-current)/avoided*100, reference must be >0. No display
  rounding is applied before comparisons; only advantage gets 1e-9 tolerance.
- Price age is [0,900) seconds by actual timestamps, not wall-clock subtraction.
  Current quarter quote must differ from observed current price by strictly
  <0.051ct; duplicate/unsorted/non-quarter starts are rejected. No fetched-at age.
  SOC/planner freshness, each of three protection modes and state units are
  aggregated by the adapter into `sources_fresh`/`protection_mode`.
- `learning.PVLearningState` is serializable by the adapter using ISO dates.
  Capture once/day, preserving unevaluated earlier probes. Learn matching day
  once; caller must prove it is completed. >=23 valid actual hourly rows,
  positive forecast and raw ratio 0..5; retain 14, median with >=3 otherwise1.
  Invalid evaluated samples still advance learned_day, never deadlock sampling.
  A zero median is a real zero correction, not a missing value.

## Fixture provenance (no measured household data)

`tests/test_planner.py` retains old synthetic regression fixtures, updated only
to the binding quarter-hour input contract. All `tests/unit` numeric inputs are
artificial constants, hand formulas or deterministic `random.Random(seed)` with
seeds0..47. No live tariff quotes, consumption traces, SOC/reserve values or
persistent learner history are copied from inventory.

The two `.jinja` fixtures are code-only extracts of evidence L's exact captured
`projection_raw` and `decision_raw` (planner actions[4].variables), not generated
approximations. Only the private tariff selector was replaced with
`fixture_tariff`; there are no entity IDs, URLs, tokens or measured values.
The private source location/hash is held outside Git in the foundation ledger.
Sanitized fixture SHA256:

- live_projection.jinja: 02cec6d8b84ddd6fe2ce0666610191dc9e4f608aaddf2e344d547fc5bf341fc4
- live_decision.jinja: ad8a1e7edbeeb00048562f44499b78160e5c760345dffd0af90b8f7d91196699

The parity test executes those actual Jinja templates with standalone Jinja2
helpers and synthetic inputs, checking projection outputs and allow/deny. Its
0.000051 absolute numeric tolerance accounts ONLY for L's final 4-decimal display
rounding. It is not used by production policy. Invalid old projection cases must
still deny; target safety/unknown-value gates are tested independently.

## Deliberate target safety distinctions

C and the binding INTERFACE require unrounded economic comparisons; unlike old
helper serialization, core retains precision through profile, projection, ratio
and decision math. Threshold tests explicitly exercise tiny differences. Raw
learning ratio bounds are checked before any presentation rounding. Unknown,
nonfinite/bool and computed-overflow values fail closed rather than using old
Jinja float defaults. Signed grid is accepted, negative reconstructed energy is
not. The mandated selected net meter and tariff/home selection are adapter
responsibilities, not fixed IDs in this core. Migration must preserve configured
nondefaults;20% is a new-install setting only, not an override in `decide`.

## Proposal and learning transitions

Eligible proposal -> runtime may consider starting/continuing ONLY after all
runtime gates. Ineligible proposal -> no new charge; active runtime must stop
and restore through its guarded journal. Full marker blocks the same solar day
after small discharge; the core neither clears the marker nor equates a plan to
a successfully persisted marker. All-full SOC returns batteries_full. A changed
solar day may start only after the adapter supplies its matching marker state.

Learning: empty -> captured -> matching evaluated -> next captured. Recapture,
wrong-day learning and repeated evaluation are no-ops. Bad/incomplete evaluated
sample advances evaluated day but retains accepted ratios. JSON/storage and
restart durability are tested by the adapter lane, not simulated by this core.
