"""Execute sanitized captured Jinja (not a second Python approximation)."""

import json
import random
from datetime import UTC, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from jinja2 import Environment, StrictUndefined
from test_economics import candidate

from custom_components.ecoflow_smart_charge.planner.core import (
    Battery,
    HourlyProfile,
    PricePoint,
    decide,
)


def oracle(c):
    env = Environment(undefined=StrictUndefined)

    def as_datetime(value):
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value, UTC)
        return datetime.fromisoformat(value) if isinstance(value, str) else value

    env.globals.update(
        as_datetime=as_datetime,
        timedelta=timedelta,
        as_local=lambda d: d.astimezone(c.now.tzinfo),
        as_timestamp=lambda d, default=0: as_datetime(d).timestamp(),
    )
    env.filters["to_json"] = json.dumps
    ctx = {
        "efficiency": c.efficiency,
        "capacity": c.capacity_kwh,
        "soc": [b.soc for b in c.batteries],
        "reserve": [b.reserve for b in c.batteries],
        "now_ts": c.now.timestamp(),
        "today": c.now.date().isoformat(),
        "solar_day": (
            c.now.date() + timedelta(days=1 if c.below_horizon and c.now.hour >= 12 else 0)
        ).isoformat(),
        "sunset_ts": c.sunset.timestamp(),
        "forecast_today": c.forecast_today,
        "forecast_tomorrow": c.forecast_tomorrow,
        "correction": c.pv_correction,
        "current": c.current_price_ct,
    }
    profile = {
        "house": c.profile.house_by_hour,
        "pv": c.profile.pv_by_hour,
        "samples": min(c.profile.samples_by_hour),
    }
    tariff = {
        "prices": {
            "fixture_tariff": [
                {"start_time": p.starts_at.isoformat(), "price": p.price_ct / 100} for p in c.prices
            ]
        }
    }
    template = Path(__file__).with_name("fixtures").joinpath("live_projection.jinja").read_text()
    return json.loads(env.from_string(template).render(ctx=ctx, profile=profile, tariff=tariff))


def decision_oracle(c, projection):
    env = Environment(undefined=StrictUndefined)
    env.filters["to_json"] = json.dumps
    template = Path(__file__).with_name("fixtures").joinpath("live_decision.jinja").read_text()
    return json.loads(
        env.from_string(template).render(
            current=c.current_price_ct,
            efficiency=c.efficiency,
            wear=c.wear_cost_ct,
            projection=projection,
            avoided_price=projection["avoided_price"],
            data_valid=projection["valid"],
            completed=c.full_marker_for_solar_day,
            needed=projection["needed"],
            ceiling=c.charge_ceiling_ct,
            active=c.active_session,
            solar_surplus=projection["solar_surplus"],
            bestprice_window=c.best_price_window,
            covered=projection["coverage"] > 0 and not projection["internal_price_gap"],
            min_price_advantage=c.minimum_price_advantage_percent,
            margin=c.minimum_net_saving_ct,
        )
    )


@pytest.mark.parametrize("seed", range(48))
def test_projection_matches_captured_live_template_on_synthetic_inputs(seed):
    rng = random.Random(seed)
    zone = ZoneInfo("Europe/Berlin")
    now = datetime(
        2026, 10 if seed % 2 else 3, 25 if seed % 2 else 29, seed % 24, 7, 30, tzinfo=zone
    )
    start = int(now.timestamp() // 900) * 900
    count = (2, 16, 48, 96, 196)[seed % 5]
    prices = tuple(
        PricePoint(
            datetime.fromtimestamp(start + i * 900, zone), 10 if i == 0 else rng.uniform(15, 55)
        )
        for i in range(count)
    )
    if seed % 7 == 0 and count > 16:
        prices = prices[:10] + prices[11:]
    profile = HourlyProfile(
        tuple(rng.uniform(0.05, 2) for _ in range(24)),
        tuple(rng.uniform(0.05, 1) if 7 <= h <= 18 else 0 for h in range(24)),
        (14,) * 24,
        True,
        "ok",
    )
    c = candidate(
        now=now,
        price_series_updated=now,
        prices=prices,
        profile=profile,
        sunset=now + timedelta(hours=18),
        forecast_today=rng.uniform(0, 4),
        forecast_tomorrow=rng.uniform(0, 8),
        below_horizon=bool(seed % 3),
        efficiency=rng.uniform(0.7, 1),
        pv_correction=rng.uniform(0.5, 1.5),
        batteries=tuple(Battery(rng.uniform(10, 99), rng.uniform(3, 40)) for _ in range(3)),
        active_session=bool(seed % 2),
    )
    old = oracle(c)
    new = decide(c)
    decision = decision_oracle(c, old)
    assert new.allowed is decision["allow"]
    if not old["valid"]:
        assert not new.allowed
        return
    for field, key in [
        ("missing_energy_kwh", "needed"),
        ("solar_surplus_kwh", "solar_surplus"),
        ("coverage_kwh", "coverage"),
        ("target_ac_kwh", "target_ac"),
        ("avoided_price_ct", "avoided_price"),
    ]:
        assert getattr(new, field) == pytest.approx(old[key], abs=0.000051)
    assert old["valid"] is (new.reason != "price_gap")
    if old["internal_price_gap"]:
        assert not new.allowed
