"""Learning/regression checks for matching days and genuine configuration values."""

from dataclasses import replace
from datetime import date, timedelta

from test_economics import candidate

from custom_components.ecoflow_smart_charge.planner.core import PricePoint, decide
from custom_components.ecoflow_smart_charge.planner.learning import (
    PVLearningState,
    capture_probe,
    learn_day,
)


def test_imported_nondefault_advantage_and_ceiling_are_not_replaced():
    c = candidate(current_price_ct=30.4, efficiency=1, wear_cost_ct=0)
    c = replace(c, prices=(PricePoint(c.now, 30.4),) + c.prices[1:])
    assert decide(c).allowed
    assert (
        decide(replace(c, minimum_price_advantage_percent=25)).reason == "price_advantage_too_low"
    )
    c = replace(c, current_price_ct=32, prices=(PricePoint(c.now, 32),) + c.prices[1:])
    assert decide(c).allowed
    assert decide(replace(c, charge_ceiling_ct=31.999999)).reason == "price_above_ceiling"


def test_learning_matching_day_no_double_evaluation_and_fourteen_valid_ratios():
    d = date(2026, 1, 1)
    s = PVLearningState((), 1.0, None, None, None)
    for i in range(16):
        today = d + timedelta(days=i)
        s = capture_probe(s, day=today, forecast_kwh=2)
        assert learn_day(s, day=today - timedelta(days=1), actual_kwh=4, hourly_rows=24) == s
        s = learn_day(s, day=today, actual_kwh=i / 2, hourly_rows=24)
    assert len(s.ratios) == 14
    assert s.ratios[0] == 0.5
    assert s.ratios[-1] == 3.75
    assert s.correction == 2.125
    assert capture_probe(s, day=s.probe_day, forecast_kwh=9) == s
    assert learn_day(s, day=s.learned_day, actual_kwh=9, hourly_rows=24) == s


def test_zero_forecast_does_not_capture_or_evaluate_ratio():
    d = date(2026, 1, 1)
    s = PVLearningState((), 1.0, None, None, None)
    for value in (0, -1, True, float("nan"), float("inf")):
        assert capture_probe(s, day=d, forecast_kwh=value) == s
    imported = PVLearningState((1, 2), 1.0, d, 0.0, None)
    assert learn_day(imported, day=d, actual_kwh=3, hourly_rows=23).ratios == (1, 2)
