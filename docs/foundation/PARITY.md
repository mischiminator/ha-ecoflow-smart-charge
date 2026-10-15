# Parity and acceptance checklist

Every row is REQUIRED. This foundation defines tests to be implemented, NOT a
claim those behaviors pass. Existing scaffold tests cover fragments only.
Lane reports docs/core, docs/adapter and docs/release must map each applicable ID
to implementation paths, actual pytest node IDs, RED/GREEN evidence and any
remaining gaps. Cross-lane reconciliation must close every row before release.
Sources are labels from SOURCES.md; exact private locations remain outside Git.

| ID | Owner | Source | Required behavior | Boundary / failure / recovery tests |
|---|---|---|---|---|
| P01 | core+HA | C Planning; L planner recorder action/profile_raw | Only selected mandated net meter; no alternate or mixed old-meter history | Wrong configured meter; no history; same rows from different meter must not be silently substituted |
| P02 | core+HA | C Planning; L profile_raw | 14 fully completed local days; exclude current-day boundary row; normalize kWh and join all 8 streams | Wh/kWh equivalence; missing stream; reset; NaN/inf/bool; signed grid export with valid load |
| P03 | core | L profile_raw | Reconstruct grid+PV-charge+discharge; load/PV in 0..10; 3+ samples each hour | 2 vs3; exactly0/10 vs outside; charge/discharge triples; 23/25-hour DST days |
| P04 | HA | C Planning; L tariff action/projection_raw | Fetch actual published configured tariff today+tomorrow; no unannounced prices | Missing selected tariff; EUR conversion; wrong home; empty response; service exception |
| P05 | core | L projection_raw | Current published quarter matches current price within strict0.051ct | At boundary; +/-epsilon; duplicate slots; off-quarter now; DST offsets |
| P06 | core | L ctx/projection_raw | Solar day next only below horizon and hour>=12; valid future sunset | Before sunrise; noon; exact sunset; after sunset; next_setting absent/past |
| P07 | core | L projection_raw | 196 quarter-hour curve; remaining first slot and per-day PV denominators | Mid-slot; zero PV profile with nonzero forecast invalid; no division by0 |
| P08 | core | L projection_raw; C Planning | Subtract interval household load; positive daylight solar surplus times sqrt(efficiency) | Equal surplus/demand blocks new start; active session exception only solar deficit |
| P09 | core | L projection_raw | Missing energy from individual SOC; existing usable energy from individual original reserves | Unequal reserves; one full battery; all full; below reserve SOC; invalid reserve |
| P10 | core | L projection_raw | Solar-adjusted future deficits consume existing usable energy before incremental target | Reserves change avoided-price weighting; no assumed constant charger watts |
| P11 | core | L decision_raw/projection_raw | Partial known tail coverage allowed; unknown tail contributes zero saving; internal gaps block | One priced useful slot; partial coverage1/2; missing internal slot; zero useful consumption |
| P12 | core | C Planning; L decision_raw | Weighted avoided reference and charge/efficiency+wear; unrounded thresholds | Net saving below/equal/above; avoid rounding display into permission |
| P13 | core+HA | C Current values; G PRICE-ADVANTAGE | New-install advantage20%; imported current threshold retained | 0/100 bounds; migrated nondefault threshold; ceiling preserved, not old generator default |
| P14 | core | L decision_raw; G PRICE-ADVANTAGE | (avoided-current)/avoided*100; epsilon1e-9 only | Below/at/above; zero/negative charge accepted if gates pass; reference<=0 blocked |
| P15 | HA | C Planning; G permission template | Fail closed stale/future/unknown required state; planner age[0,1200), price[0,900), SOC[0,600) | Exact exclusive limits; timestamp future; fetch time is not source timestamp; missing unit |
| P16 | core+HA | C Planning; L planner/controller | Best-price window required even if economics favorable; protection modes all3 | Window closes during session; one switch off; one select AI/unknown; no mode-changing service |
| P17 | core+HA | C PV learning; L learner/sample | One early probe daily; preserve unevaluated previous probe across restart | Same-day recapture; midnight restart; learner/sample race; no forecast |
| P18 | core+HA | L learner/sample | Learn completed matching day once; >=23 valid rows; ratios0..5; retain14; median>=3 | 22/23/25 rows; ratio0/5/outlier; zero forecast; repeated learned day; oldest trimmed |
| S01 | HA | C Session; R storage | Persist3 original reserves and intent successfully before commands | Save throws/cancelled; zero services; never update original after100% readback |
| S02 | HA | C Session; R single writer | One serialized writer across UI,timer,event; unique persistent command IDs | Concurrent start/recalculate/restore; partial service failure; timeout; retry only pending |
| S03 | HA | C Session | Independent readback per device; service acknowledgement not success | ACK but stale/unchanged state; unavailable; only2 restored; all3 then clear |
| S04 | HA | C Session; R recovery | Recovery on loss/master/full/disable/reload/unload/restart; retain pending | Crash before save/after save/before call/after call/before readback; bounded retries |
| S05 | core+HA | C full marker; L controller | Persist solar-day full marker before restore; survives session deletion | Full then slight discharge; same-day reload; solar-day rollover; marker save failure |
| S06 | HA | C Shadow; R gatekeeper | Default absolute shadow; zero hardware services on every route | Restore button with pending journal; unload; timer; restart; service; recovery stays pending |
| S07 | HA | C Cutover; R conflicts | Explicit safe approval after comparison and conflict clearance; recheck before every write | Legacy writer on/unknown/unavailable; changed mapping; arbitrary external writer limitation |
| S08 | HA | C Session; R storage | Versioned journal; invalid state blocks, never silently discarded | Malformed JSON payload/schema; out-of-range reserve; unknown version; original mapping changed |
| H01 | HA | C Entity mapping; R ConfigFlow | Selectable source/device bindings, required triples, duplicates and units validated | Invalid/missing entity; fewer/more3; duplicate entry; options reload; no hardcoded private defaults |
| H02 | HA | L triggers; R cleanup | Planner quarter-hour at second5; safety minute; source changes; learning timers; cleanup | Repeated reload; listener/timer count; no callback after unload; startup pending; Recorder absent |
| H03 | HA | R entities/services | Six native platforms, stable entry+key unique IDs; entry-targeted services through runtime | Actual hass state/service registry; entity removal; wrong entry; no UI bypass |
| H04 | HA | R Recorder; H | Blocking Recorder statistics in recorder executor, real populated SQLite tests | Valid and incomplete histories; DST; Wh/kWh; no fake-only hass acceptance |
| H05 | HA+package | C migration; R diagnostics | Supported validated preview/import settings, learning, sessions, marker; no storage edits | Invalid/incomplete import no save/no command; existing session not replaced; redacted diagnostics |
| H06 | HA+package | C Card; K setConfig and service handlers | Opt-in card adapter spec covering master/settings/status and3 batteries | Native switch vs old input_boolean validation; native number vs input_number services; old dashboard unchanged |
| D01 | package | R packaging_ci | Manifest/HACS/license/brand/translations/services align; versioned tested release | JSON/schema mismatch; missing locale key; provenance/license; no fabricated release success |
| D02 | package | R tests/CI; H | Pinned compatible Python/HA/plugin, pytest/ruff/hassfest/HACS workflows | Run local permitted validations; remote actions not run must say so |
| D03 | package | C privacy/rollback | No raw inventory, credentials, IDs/home URLs or backups; safe migration/rollback guide | Scan tree AND Git history; acknowledge historical exposure; shadow cannot restore by itself |

## Release gates

- [ ] All row IDs have passing actual tests, not planned names.
- [ ] Synthetic fixtures have formula/provenance notes; no copied household traces.
- [ ] Grid-source transition differences documented independently of parity.
- [ ] Real HA flow/lifecycle/Recorder/service/entity tests executed.
- [ ] Crash matrix, shadow-zero-call and readback tests executed.
- [ ] All lanes load TDD skill and preserve failed-first logs.
- [ ] Secret/private-identifier scan covers candidate tree and publishable history.
- [ ] Migration/card/service/schema documentation aligned with final code.
- [ ] Local commit, exact test logs, limitations and release artifact recorded.
- [ ] No production or GitHub action claimed without separate authorization.
