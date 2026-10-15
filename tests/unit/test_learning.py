"""Artificial daily ratios exercise the persistence-free state transitions."""

from datetime import date, timedelta

import pytest

from custom_components.ecoflow_smart_charge.planner import core


def test_probe_survives_restart_and_cannot_be_replaced_before_learning():
    # Attribute assertion makes the first RED explicit, not an import/collection error.
    from importlib.util import find_spec

    assert find_spec("custom_components.ecoflow_smart_charge.planner.learning") is not None
    from custom_components.ecoflow_smart_charge.planner import learning

    assert hasattr(learning, "PVLearningState")
    state = learning.PVLearningState((), 1.0, None, None, None)
    day = date(2026, 1, 1)
    state = learning.capture_probe(state, day=day, forecast_kwh=2.0)
    assert learning.capture_probe(state, day=day, forecast_kwh=3.0) == state
    assert learning.capture_probe(state, day=day + timedelta(days=1), forecast_kwh=3.0) == state
    learned = learning.learn_day(state, day=day, actual_kwh=4, hourly_rows=23)
    assert learned.ratios == (2.0,)
    assert learned.correction == 1.0
    assert learned.learned_day == day
    assert learning.learn_day(learned, day=day, actual_kwh=8, hourly_rows=23) == learned
    assert learning.capture_probe(
        learned, day=day + timedelta(days=1), forecast_kwh=3
    ).probe_day == day + timedelta(days=1)


@pytest.mark.parametrize(
    "actual,count,ratios",
    [
        (0, 23, (1, 2, 0)),
        (10, 25, (1, 2, 5)),
        (10.01, 24, (1, 2)),
        (float("nan"), 24, (1, 2)),
        (2, 22, (1, 2)),
    ],
)
def test_evaluated_days_advance_even_if_ratio_invalid(actual, count, ratios):
    from custom_components.ecoflow_smart_charge.planner import learning

    d = date(2026, 1, 1)
    s = learning.PVLearningState((1, 2), 1.0, d, 2, None)
    result = learning.learn_day(s, day=d, actual_kwh=actual, hourly_rows=count)
    assert result.ratios == ratios
    assert result.learned_day == d
    assert result.correction == (sorted(ratios)[1] if len(ratios) == 3 else 1)


def test_zero_median_is_a_real_learned_correction_not_neutral():
    from custom_components.ecoflow_smart_charge.planner.learning import PVLearningState, learn_day

    d = date(2026, 1, 1)
    s = PVLearningState((0.0, 0.0), 1.0, d, 2.0, None)
    assert learn_day(s, day=d, actual_kwh=0.0, hourly_rows=23).correction == 0.0


def test_learning_facade_rejects_nonfinite_and_bool():
    assert core.learn_pv_correction([1, 2], actual_kwh=True, forecast_kwh=2, hourly_rows=24) == (
        1,
        2,
    )
    assert core.correction_from_ratios([True, float("nan"), 2]) is None
