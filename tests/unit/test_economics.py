"""Hand-calculated artificial quarter-hour economics, not a tariff forecast."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from custom_components.ecoflow_smart_charge.planner.core import (
    Battery,
    HourlyProfile,
    PlannerInput,
    PricePoint,
    decide,
)


def candidate(**overrides):
    now = datetime(2026, 1, 4, 12, tzinfo=UTC)
    data = {
        "now": now,
        "prices": tuple(
            PricePoint(now + timedelta(minutes=15 * i), 10 if i == 0 else 40) for i in range(97)
        ),
        "price_series_updated": now,
        "best_price_window": True,
        "profile": HourlyProfile((1.0,) * 24, (1.0,) * 24, (14,) * 24, True, "ok"),
        "forecast_today": 0.0,
        "forecast_tomorrow": 0.0,
        "pv_correction": 1.0,
        "sunset": now + timedelta(hours=5),
        "batteries": (Battery(50, 3),) * 3,
        "capacity_kwh": 2.0,
        "efficiency": 0.81,
        "wear_cost_ct": 2.0,
        "charge_ceiling_ct": 32.0,
        "minimum_net_saving_ct": 3.0,
        "minimum_price_advantage_percent": 20.0,
        "active_session": False,
        "full_marker_for_solar_day": False,
        "protection_mode": True,
        "current_price_ct": 10.0,
        "below_horizon": False,
    }
    data.update(overrides)
    return PlannerInput(**data)


def test_partial_tail_coverage_sqrt_target_and_individual_reserves():
    # Needed 3 kWh DC => target 2.7 AC; originals at SOC leave zero baseline.
    # One future quarter delivers .25 AC, no fabricated tail. Saving scaled .25/2.7.
    c = candidate(batteries=(Battery(50, 50),) * 3)
    c = replace(c, prices=c.prices[:2], minimum_net_saving_ct=0)
    p = decide(c)
    assert p.allowed
    assert p.missing_energy_kwh == 3
    assert p.target_ac_kwh == pytest.approx(2.7)
    assert p.coverage_kwh == 0.25
    assert p.coverage_fraction == pytest.approx(0.25 / 2.7)
    assert p.avoided_price_ct == 40
    assert p.cost_ct == pytest.approx(10 / 0.81 + 2)
    assert p.net_saving_ct == pytest.approx((40 - (10 / 0.81 + 2)) * 0.25 / 2.7)
    assert p.command_plan == ()
