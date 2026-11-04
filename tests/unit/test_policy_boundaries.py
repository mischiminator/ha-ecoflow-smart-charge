"""Regression boundaries for supported policy; these tests may already pass."""

from dataclasses import replace
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from test_economics import candidate

from custom_components.ecoflow_smart_charge.planner.core import Battery, PricePoint, decide
from custom_components.ecoflow_smart_charge.planner.forecast import build_curve


@pytest.mark.parametrize(
    "delta,allowed", [(-1e-8, True), (0, True), (1e-10, True), (3e-10, False), (1e-8, False)]
)
def test_advantage_unrounded_with_only_one_e_minus_nine_tolerance(delta, allowed):
    c = candidate(efficiency=1, wear_cost_ct=0, current_price_ct=20 + delta)
    c = replace(
        c,
        prices=tuple(
            replace(p, price_ct=20 + delta if i == 0 else 25) for i, p in enumerate(c.prices)
        ),
    )
    assert decide(c).allowed is allowed


@pytest.mark.parametrize("delta,allowed", [(-1e-10, True), (0, True), (1e-10, False)])
def test_net_saving_has_no_epsilon_or_display_rounding(delta, allowed):
    c = candidate(
        efficiency=1,
        wear_cost_ct=0,
        current_price_ct=20 + delta,
        minimum_net_saving_ct=5,
        minimum_price_advantage_percent=0,
    )
    c = replace(
        c,
        prices=tuple(
            replace(p, price_ct=20 + delta if i == 0 else 25) for i, p in enumerate(c.prices)
        ),
    )
    assert decide(c).allowed is allowed


@pytest.mark.parametrize("price", [0, -10])
def test_zero_negative_charge_prices_accepted_with_positive_reference(price):
    c = candidate(current_price_ct=price, minimum_price_advantage_percent=100)
    assert decide(replace(c, prices=(PricePoint(c.now, price),) + c.prices[1:])).allowed


@pytest.mark.parametrize(
    "threshold,allowed",
    [
        (-0.001, False),
        (0, True),
        (100, False),
        (100.001, False),
        (float("nan"), False),
        (True, False),
    ],
)
def test_configured_threshold_bounds_and_preservation(threshold, allowed):
    assert decide(candidate(minimum_price_advantage_percent=threshold)).allowed is allowed


def test_reference_nonpositive_is_not_economic_permission():
    c = candidate(current_price_ct=-10)
    c = replace(
        c, prices=tuple(replace(p, price_ct=-10 if i == 0 else 0) for i, p in enumerate(c.prices))
    )
    assert decide(c).reason == "nonpositive_reference_price"


def test_original_reserves_change_weighting_not_missing_energy():
    c = candidate(batteries=(Battery(100, 100), Battery(50, 50), Battery(0, 3)), efficiency=1)
    c = replace(
        c,
        prices=tuple(
            replace(p, price_ct=10 if i == 0 else 100 if i < 5 else 30)
            for i, p in enumerate(c.prices)
        ),
    )
    p = decide(c)
    q = decide(replace(c, batteries=(Battery(100, 3), Battery(50, 3), Battery(0, 3))))
    assert p.missing_energy_kwh == q.missing_energy_kwh == 3
    assert p.avoided_price_ct == pytest.approx((100 + 60) / 3)
    assert q.avoided_price_ct == pytest.approx(30)


@pytest.mark.parametrize(
    "overrides,reason",
    [
        ({"protection_mode": False}, "protection_mode_required"),
        ({"best_price_window": False}, "outside_best_price_window"),
        ({"full_marker_for_solar_day": True}, "already_full_for_solar_day"),
        ({"batteries": (Battery(100, 3),) * 3}, "batteries_full"),
        ({"charge_ceiling_ct": 9.999}, "price_above_ceiling"),
    ],
)
def test_active_session_never_bypasses_safety_gates(overrides, reason):
    assert decide(candidate(active_session=True, **overrides)).reason == reason


def test_full_marker_blocks_small_discharge_then_new_day_can_plan():
    c = candidate(batteries=(Battery(99.9, 3),) * 3, full_marker_for_solar_day=True)
    assert decide(c).reason == "already_full_for_solar_day"
    assert decide(replace(c, full_marker_for_solar_day=False)).allowed


@pytest.mark.parametrize(
    "day",
    [
        datetime(2026, 3, 29, tzinfo=ZoneInfo("Europe/Berlin")),
        datetime(2026, 10, 25, tzinfo=ZoneInfo("Europe/Berlin")),
    ],
)
def test_curve_196_elapsed_quarters_across_dst(day):
    c = candidate(now=day, sunset=day + timedelta(hours=18))
    curve = build_curve(c)
    assert len(curve.rows) == 196
    assert all(b.ts - a.ts == 900 for a, b in zip(curve.rows, curve.rows[1:]))
    assert curve.rows[-1].ts - curve.rows[0].ts == 195 * 900


def test_no_coverage_is_not_full_coverage():
    c = candidate()
    p = decide(replace(c, prices=c.prices[:1]))
    assert p.reason == "insufficient_priced_consumption"
    assert p.coverage_kwh == 0
