# Boundary contract v1 (binding target, not implemented parity claim)

## Existing compatibility facade

All pure public symbols remain importable from planner/core.py:
Battery(soc, reserve); PricePoint(starts_at, price_ct);
HourlyProfile(house_by_hour, pv_by_hour, samples_by_hour, valid, reason);
PlannerInput and PlanResult; build_hourly_profile; decide;
learn_pv_correction; correction_from_ratios. Keep existing constructor fields and
ordering. Core owns additive optional fields specified below; adapter does not
edit their definitions. Existing runtime/store signatures may be safely extended
by the adapter; the core must never depend on them.

The existing scaffold is incomplete. This document defines the implementation
contract for downstream tasks, not a set of production stubs to fill silently.

## Immutable pure inputs, units and time

Numbers finite, booleans not accepted as numbers. Three ordered battery slots
(0,1,2); reserve is original individual pre-session reserve while active, NOT a
readback of the temporary 100% command. SOC 0..100, physical reserve 3..100.
Energy kWh, prices ct/kWh, efficiency fraction (0,1], percentage points 0..100.
All timestamps timezone-aware; arithmetic/joins in UTC, bucket/day selection in
installation ZoneInfo. Quarter-hour price starts refer to actual instants; never
subtract wall-clock times across DST. No NaN, infinity, naive time or unknown
required values converted into a permissive fallback.

Recorder row shape retained: {start: aware datetime in local zone, grid: float,
pv: float, charges: tuple[float,float,float], discharges: same}. Adapter joins
all eight statistic streams by UTC start and converts energy to kWh; missing row
remains invalid, not zero. Core build_hourly_profile(rows, *, now=None) adds an
optional aware now for strict local [midnight-14 days, midnight) filtering.
Adapter MUST pass now; old no-now callers remain test compatibility only.
Aggregate actual repeated fall-back hours as independent elapsed-hour samples;
missing spring-forward hour is absent, not fabricated. At least 3 samples in
each of 24 local-hour buckets. Preserve L's 0..10 kWh load/PV plausibility cap.

PlannerInput retains all existing fields. Add these optional fields at the end:
current_price_ct: float | None = None; below_horizon: bool | None = None.
None means insufficient evidence for an active decision (update old synthetic
fixtures accordingly); never infer sun state or current price from a fabricated
quote. now carries local timezone; sunset is the future sun next_setting instant.
forecast_today means REMAINING today's forecast, tomorrow means full next-day.
price_series_updated is the source price timestamp, not time of fetching it.
Existing sources_fresh includes SOC/report age, planner age, required state/unit
validity; master is a separate runtime gate. best_price_window remains required.

PricePoint uses L's published quarter-hour starts; price_ct is converted once
from EUR/kWh by adapter. Fetch only the configured tariff/home key, never first
available. No tomorrow fabrication. Price validation checks current interval
against current_price_ct (absolute difference strictly <0.051 ct), duplicates,
sorted UTC starts and internal gaps only in the horizon actually traversed.

## Pure projection and result

Core decide(PlannerInput) -> PlanResult is deterministic, performs no I/O and
never contains executable HA services in command_plan (retain empty tuple).
The result is a proposal only; all gates must be rechecked before each command.
Add optional diagnostic fields at end: solar_day: str | None = None,
coverage_kwh: float = 0.0, target_ac_kwh: float = 0.0,
coverage_fraction: float = 0.0, cost_ct: float = 0.0.
Reason is a stable English machine code, translated by adapter presentation.
No display rounding before price-advantage or saving comparisons.

Reproduce L: sqrt(efficiency) for usable baseline and delivered target; 196
quarter-hour rows from floor(now/900), first row uses remaining fraction; choose
next solar day only when below_horizon AND local hour>=12, otherwise today.
Distribute remaining today/tomorrow corrected forecast using hourly PV scores
and separate day denominators. Solar surplus is daylight positive solar-load
multiplied by sqrt(efficiency). Projection starts AFTER current slot, subtracts
solar from load and existing usable energy first. Coverage may be partial at
unpublished tail: avoided=value/covered; saving=(avoided-cost)*min(covered/target,1).
Coverage must be positive, internal missing published slots block. No fixed
charger power, daily maximum-price proxy or hourly unscaled substitute.

## Pure PV learning, adapter persistence

Add planner/learning.py with frozen PVLearningState(ratios: tuple[float,...],
correction: float, probe_day: date | None, probe_kwh: float | None,
learned_day: date | None). Pure functions:
capture_probe(state, *, day: date, forecast_kwh: float) -> PVLearningState;
learn_day(state, *, day: date, actual_kwh: float, hourly_rows: int) -> PVLearningState.
Probe is once/day; do not replace unevaluated earlier probe. Learn only matching
probe day, only after that day has completed (adapter supplies yesterday), never
twice. >=23 valid hourly rows, positive forecast, ratio 0..5, retain 14 ratios;
median with >=3 accepted ratios, else neutral correction 1 (L). An evaluated
invalid ratio retains the prior ratio series; record the evaluated day as L does,
so an invalid sample cannot permanently prevent future daily probes. Incomplete
data is not falsely accepted as a ratio. Adapter validates
actual rows/day and persists returned state before exposing it. Serialization is
adapter-owned JSON using ISO dates; pure core imports no HA/storage library.

## Session journal and single device executor

Runtime is sole entry-local serialized writer (one lock covers event/timer/UI
requests). Config entry runtime_data contains reader/coordinator, journal,
learning state, listener/timer cancels and last plan. Entities/services call
runtime methods only. Source readers return one immutable snapshot for decide;
Recorder queries run in recorder executor. Recalculate/start/retry revalidate
master, mode, fresh state, price/window, plan age, marker and conflict lock.

Versioned integration-owned Store envelope:
{schema_version: 1, session: null | SessionRecord, learning: {...},
 full_marker_day: null | ISO-date}. Keep full marker after session clear.
SessionRecord holds session_id, created_at, original reserves per slot,
configured writer identity per slot, pending targets, per-target command_id,
phase, readback evidence and planned solar day. Existing reserves_before and
pending_targets compatibility can be migrated into this envelope explicitly.
Reject malformed stores, unknown versions or mismatched mappings as recovery
blocked; NEVER silently drop a safety record. Entity IDs may be private runtime
mapping data, never public fixtures/defaults or stable identity keys.

Save entire validated pre-session reserve capture and intent with awaited
Store.async_save BEFORE hardware command; save failure/cancellation sends no
command. Commit in-memory phase only after successful save. Journal is not
RestoreEntity or delayed telemetry save. Each intended retry is persisted before
service; acknowledgement is not confirmation. Executor writes only selected
number.set_value target with blocking=True, then observes a fresh independent
state readback matching desired value; unavailable/old state remains pending.
Do not overwrite originals on retry. Recover only unconfirmed slots; all three
must confirm before clearing journal. Exceptions/timeouts retain intent.

Allowed phases: idle -> intent_persisted -> charge_pending -> charging ->
restore_pending -> idle. Any crash with session -> recovery_pending; corrupt
state -> recovery_blocked. Full SOCs persist marker BEFORE restore. Master off,
permission loss, stale inputs, mode/window failure, full, disable, reload/unload
initiate stop and never start again. Unload cancels starts/listeners/timers,
tries bounded restoration under authorized active ownership; if pending, retain
journal and expose/raise failed safe unload rather than claim success. Restart
never auto-reenters active; return shadow with recovery_pending.

Shadow is absolute: ZERO hardware services including restore, recovery button,
timer, unload or replay. A pending legacy/active session in shadow remains visible
and blocks cutover; explicit operator-authorized recovery transitions through the
same guarded executor OUTSIDE shadow, with conflict clearance, then returns to
shadow. No automatic recovery mode switch. Price/mode failures block charging,
not restoring original safe values; restoration still requires exclusive writer
ownership and known saved targets. Do not require charging economics for restore.

Cutover requires explicit confirmation, successful recorded shadow comparison,
current full validity, no pending session and confirmed original reserves,
configured legacy command writers OFF. Unknown/missing conflict state blocks.
Recheck ownership before EVERY hardware call. Cannot prove absence of arbitrary
third-party writers: document limitation. No automatic disabling external entities.

## Migration and service/UI boundary

Config data: selected grid/PV/forecast/price/window/sun/statistic sources and
three SOC/reserve/mode/switch/charge/discharge bindings; tariff selector and legacy
writer selections. Options: bounded economic settings/master/mode. Entry updates
through HA supported manager APIs; options reload listener has cleanup.
New-install advantage default20%; imports preserve selected existing values,
never substitute defaults for migration values. No private default entity IDs.

Services recalculate, request_cutover, confirm_recovery require config_entry_id;
new import service/flow belongs to adapter and must validate the versioned envelope
before save, produce preview, never command devices or edit HA .storage directly.
Card mapping must cover all status/settings and three batteries. K currently
restricts master to input_boolean and calls legacy helper services: entity mapping
alone is NOT enough for a native switch/number. Do not modify K here; provide a
separate opt-in adapter/card update specification and preserve old dashboard.
