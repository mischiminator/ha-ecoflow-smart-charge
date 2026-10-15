# Executed vertical core TDD record

Base commit for these sequential worktree slices:
`5bd40d4b5fa3b151bfc501e4082448baf8a39bf7`.
TDD skill was loaded before code edits. All commands ran with the absolute
interpreter provided by foundation DEVELOPMENT.md (Python3.14.7, pytest9.0.3,
HA2026.10.1/plugin0.13.372). Below `python` means that pinned interpreter, not
an arbitrary system Python. Log names are relative to this directory. Captured log line-end whitespace was
trimmed for Git whitespace checks; assertions, outputs and outcomes are unchanged.

## C01 — P02/P03, complete-day Recorder reconstruction

Behavior: average valid signed-net eight-stream rows in14 completed local days,
count DST repetitions as elapsed samples and reject bad numbers/row shapes.
RED_command: python -m pytest tests/unit/test_profile.py -q
RED_exit:1;7 failed, missing required now keyword (feature absent), no collection
failure. Actual log:01-profile-red.log.
Change: core.build_hourly_profile; validation.number/aware.
GREEN: same focused cases included with legacy test_planner.py;16 passed, exit0.
Regression command: python -m pytest tests/unit/test_profile.py tests/test_planner.py -q
Actual log:01-profile-green.log. Refactor:none at this stage.

## C02 — P17/P18, persistent-value-compatible daily learning transitions

Behavior: once-daily immutable probe/evaluation with pending-probe preservation,
matching day, ratio acceptance and neutral correction with too few samples.
RED_command: python -m pytest tests/unit/test_learning.py -q
RED_exit:1;7 failed. Explicit find_spec assertion proves absent learning module;
other cases report missing learning import; helper assertion exposes bool accepted
as0.5 ratio. Actual log:02-learning-red.log. The import failures are feature
absence, not syntax/collection errors; not claimed as seven independent bugs.
Change: planner/learning.py and compatibility facade helper reexports.
GREEN/regression: python -m pytest tests/unit tests/test_planner.py -q
23 passed,exit0;02-learning-green.log. Refactor:helpers moved into pure learning.

## C03 — P09/P10/P11/P12, partial-tail quarter-hour economic tracer

Behavior: with original reserve=SOC, one known future quarter covers0.25 of
2.7kWh delivered target, reference40 and coverage-scaled net; no invented tail.
RED_command: python -m pytest tests/unit/test_economics.py -q
RED_exit:1;1 failed for missing binding additive current_price_ct input.
Actual log:03-economics-red.log.
Change: additive input/output fields, core.decide quarter-hour projection,
sqrt-efficiency target/baseline, partial coverage, diagnostics. Update owned old
synthetic fixtures to quarter-hours and explicit current quote/sun state.
GREEN/regression: python -m pytest tests/unit tests/test_planner.py -q
24 passed,exit0;03-economics-green.log. Refactor:removed hourly proxy projection.

## C04 — P05/P15/P16, fail-closed snapshot/price validation

Behavior: complete required input gates and actual published current quarter,
strict price age/quote limits; gaps outside traversed demand are irrelevant.
RED_command: python -m pytest tests/unit/test_validation.py -q
RED_exit:1;22 failed,7 passed. Assertions expose future/exact900s accepted,
None/bool/NaN inputs allowed, absent strict quote match, sorted input accepted,
and an untraversed gap incorrectly rejected. Naive times also raised TypeError.
Actual log:04-validation-red.log. Existing already-safe cases are regression,
not represented as newly failing TDD cases.
Change: core._reason with numeric/time/shape/state validation, per-traversal gap
validation in decide; use observed current price in cost/advantage after matching.
GREEN/regression: python -m pytest tests/unit tests/test_planner.py -q
53 passed,exit0;04-validation-green.log. Refactor:remove inferred hourly spacing.

## C05 — P06/P07/P08/P10, exact live PV curve tracer

Behavior: remaining first quarter, separate day denominators, selected solar day,
sqrt-surplus and solar-adjusted projected deficits.
RED_command: python -m pytest tests/unit/test_solar.py -q
RED_exit:1;4 failed,1 passed. Observed solar_day None, incorrect whole-day
surplus3 rather than2.8125, and avoided84.4444 rather than40 when future solar
should eliminate expensive daytime deficits. Actual log:05-solar-red.log.
Change: planner/forecast.py actual196-slot curve, integrate into decide.
GREEN/regression: python -m pytest tests/unit tests/test_planner.py -q
58 passed,exit0;05-solar-green.log. Refactor:remove old daily PV shortcut.

## C06 — P18, zero correction is not missing

Behavior: three accepted zero ratios yield correction0, not neutral1.
RED_command: python -m pytest tests/unit/test_learning.py::test_zero_median_is_a_real_learned_correction_not_neutral -q
RED_exit:1;1 failed, actual correction1.0 vs expected0.0.
Actual log:06-zero-median-red.log.
Change: distinguish None median from numeric zero in learning.learn_day.
GREEN/regression: python -m pytest tests/unit tests/test_planner.py -q
59 passed,exit0;06-zero-median-green.log. Refactor:none.

## C07 — broader already-implemented boundary regression (not retroactive TDD)

Added unrounded advantage/net threshold, zero/negative price, nonpositive
reference, unequal original reserves, full marker, ceiling, active safety and
DST196-slot cases. No production changes needed.
Command: python -m pytest tests/unit tests/test_planner.py -q
87 passed,exit0;07-boundaries-regression.log. These are regression evidence,
NOT falsely labeled failed-first feature implementations.

## C08 — derived-overflow fail-closed hardening

Behavior: finite inputs whose multiplication overflows cannot produce permission.
RED_command: python -m pytest tests/unit/test_validation.py::test_nonfinite_derived_projection_is_rejected -q
RED_exit:1;1 failed. Active session with1e308 forecast/correction produced allowed
plan with solar_surplus=inf. Actual log:08-overflow-red.log.
Change: validate computed curve, missing/target/baseline and economic outputs.
GREEN plus full parity regression: python -m pytest tests/unit tests/test_planner.py -q
136 passed,exit0;08-overflow-green-and-parity.log.
The added48 exact-template Jinja comparisons are verification of previous slices,
not a second production implementation. During oracle setup the missing timedelta
helper and expectations for diagnostics of deliberately invalid forecasts were
corrected in the TEST adapter; not claimed as production RED/GREEN fixes.

## Final refactor/verification

- Ruff0.17.0 is taken from packaging's pinned requirements-lint.txt, executed via
  uvx without modifying the frozen HA harness. Scoped check and format now pass.
- Kept explicit __all__ compatibility facade after formatter/unused-import
  cleanup briefly exposed a lost helper reexport; collection was rerun to green.
- Added actual complete-package python -S isolation and more already-supported
  profile/configuration/learning regression boundaries, no production additions.
- An initial direct --disable-socket invocation omitted --allow-unix-socket;
  the HA plugin could not create its own event-loop socketpair. Correct invocation
  below blocks IP networking while permitting that local implementation detail.

Final command:
python -m pytest tests/unit tests/test_planner.py -q --disable-socket --allow-unix-socket --junitxml=docs/tdd/core/core-tests.xml
Final exit:0;148 passed,0 failures/errors/skips. Actual core-tests.log/XML.

Scope limitation: one intermediate whole-repo run during parallel lanes had
13 failed/158 passed; full-integration-check.log retains that honest result.
The later final full runner check had202 passed/1 failed; final-integration-check.log
records the sole remaining frozen foundation standalone-loader incompatibility.
Core-owned tests are green, NOT a claim all HA/release criteria are green.
See docs/core/PARITY.md and board handoff for frozen loader/mixed-fixture
reconciliation. No source repositories, live HA, devices or GitHub changed.
