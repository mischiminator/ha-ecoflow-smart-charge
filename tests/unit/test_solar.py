"""Analytic single-solar-hour fixtures pin fractions and separate day denominators."""

from dataclasses import replace
from datetime import timedelta

import pytest
from test_economics import candidate

from custom_components.ecoflow_smart_charge.planner.core import Battery, HourlyProfile, decide


def solar_profile():
    return HourlyProfile(
        (1.0,) * 24, tuple(1.0 if h == 12 else 0.0 for h in range(24)), (14,) * 24, True, "ok"
    )


def test_remaining_first_quarter_separate_day_denominators_and_sqrt_surplus():
    c = candidate(profile=solar_profile(), forecast_today=4, forecast_tomorrow=8)
    c = replace(c, now=c.now + timedelta(minutes=7, seconds=30), sunset=c.now + timedelta(hours=1))
    p = decide(c)
    assert p.solar_day == "2026-01-04"
    assert p.solar_surplus_kwh == pytest.approx((4 - 0.875) * 0.9)
    assert p.allowed


def test_next_solar_day_only_below_horizon_after_noon():
    c = candidate(profile=solar_profile(), forecast_today=0, forecast_tomorrow=8)
    c = replace(
        c,
        now=c.now + timedelta(hours=6),
        price_series_updated=c.now + timedelta(hours=6),
        sunset=c.now + timedelta(days=1, hours=5),
        current_price_ct=40,
        charge_ceiling_ct=50,
        below_horizon=True,
    )
    p = decide(c)
    assert p.solar_day == "2026-01-05"
    assert p.solar_surplus_kwh == pytest.approx(6.3)
    assert p.reason == "solar_surplus_sufficient"


def test_before_sunrise_uses_today_and_zero_denominator_forecast_is_invalid():
    c = candidate()
    c = replace(
        c,
        now=c.now - timedelta(hours=8),
        price_series_updated=c.now - timedelta(hours=8),
        below_horizon=True,
        prices=tuple(replace(p, starts_at=p.starts_at - timedelta(hours=8)) for p in c.prices),
    )
    assert decide(c).solar_day == "2026-01-04"
    p = replace(c.profile, pv_by_hour=(0.0,) * 24)
    assert not decide(replace(c, profile=p, forecast_today=1)).allowed
    assert decide(replace(c, profile=p)).allowed


def test_future_solar_deficit_consumes_baseline_before_incremental_energy():
    # No baseline. 4 kWh solar removes the 3 future 12:xx consumption slots.
    c = candidate(profile=solar_profile(), forecast_today=4, batteries=(Battery(50, 50),) * 3)
    c = replace(
        c,
        prices=tuple(
            replace(p, price_ct=(200 if 0 < i < 4 else p.price_ct)) for i, p in enumerate(c.prices)
        ),
    )
    p = decide(c)
    assert p.avoided_price_ct == pytest.approx(40)


def test_active_session_only_bypasses_solar_start_gate():
    c = candidate(profile=solar_profile(), forecast_today=8)
    assert decide(c).reason == "solar_surplus_sufficient"
    assert decide(replace(c, active_session=True)).allowed
    assert not decide(replace(c, active_session=True, best_price_window=False)).allowed
