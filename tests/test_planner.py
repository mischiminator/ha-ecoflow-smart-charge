"""Behavioral tests for the HA-independent safety planning core."""

from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta

from custom_components.ecoflow_smart_charge.planner.core import (
    Battery,
    PlannerInput,
    PricePoint,
    build_hourly_profile,
    decide,
    learn_pv_correction,
)


def complete_rows(days: int = 3) -> list[dict[str, object]]:
    rows = []
    start = datetime(2026, 1, 1, tzinfo=UTC)
    for day in range(days):
        for hour in range(24):
            stamp = start + timedelta(days=day, hours=hour)
            rows.append(
                {
                    "start": stamp,
                    "grid": 1.0,
                    "pv": 0.2 if 8 <= hour <= 16 else 0.0,
                    "charges": (0.1, 0.1, 0.1),
                    "discharges": (0.2, 0.2, 0.2),
                }
            )
    return rows


def valid_input(**overrides: object) -> PlannerInput:
    now = datetime(2026, 1, 4, 12, tzinfo=UTC)
    prices = tuple(
        PricePoint(now + timedelta(minutes=15 * h), 10.0 if h == 0 else 30.0) for h in range(96)
    )
    data: dict[str, object] = {
        "now": now,
        "prices": prices,
        "price_series_updated": now,
        "best_price_window": True,
        "profile": build_hourly_profile(complete_rows()),
        "forecast_today": 0.0,
        "forecast_tomorrow": 0.0,
        "pv_correction": 1.0,
        "sunset": now + timedelta(hours=4),
        "batteries": (
            Battery(soc=50, reserve=3),
            Battery(soc=50, reserve=3),
            Battery(soc=50, reserve=3),
        ),
        "capacity_kwh": 2.0,
        "efficiency": 0.85,
        "wear_cost_ct": 2.0,
        "charge_ceiling_ct": 32.0,
        "minimum_net_saving_ct": 3.0,
        "minimum_price_advantage_percent": 20.0,
        "active_session": False,
        "full_marker_for_solar_day": False,
        "sources_fresh": True,
        "protection_mode": True,
        "current_price_ct": 10.0,
        "below_horizon": False,
    }
    data.update(overrides)
    return PlannerInput(**data)


class ProfileTests(unittest.TestCase):
    def test_requires_three_valid_samples_for_every_hour(self) -> None:
        profile = build_hourly_profile(complete_rows(2))
        self.assertFalse(profile.valid)
        self.assertIn("insufficient", profile.reason)

    def test_reconstructs_house_load_from_grid_pv_and_batteries(self) -> None:
        profile = build_hourly_profile(complete_rows())
        self.assertTrue(profile.valid)
        self.assertAlmostEqual(profile.house_by_hour[0], 1.3)
        self.assertAlmostEqual(profile.pv_by_hour[12], 0.2)


class PolicyTests(unittest.TestCase):
    def test_shadow_can_plan_but_never_commands(self) -> None:
        result = decide(valid_input())
        self.assertTrue(result.allowed)
        self.assertEqual(result.command_plan, ())

    def test_internal_price_gap_fails_closed(self) -> None:
        candidate = valid_input()
        prices = candidate.prices[:2] + (PricePoint(candidate.now + timedelta(hours=3), 30.0),)
        result = decide(valid_input(prices=prices))
        self.assertFalse(result.allowed)
        self.assertEqual(result.reason, "price_gap")

    def test_unrounded_price_advantage_blocks_below_threshold(self) -> None:
        now = datetime(2026, 1, 4, 12, tzinfo=UTC)
        prices = tuple(
            PricePoint(now + timedelta(minutes=15 * h), 20.0000000003 if h == 0 else 25.0)
            for h in range(96)
        )
        result = decide(
            valid_input(
                prices=prices, current_price_ct=20.0000000003, minimum_price_advantage_percent=20.0
            )
        )
        self.assertFalse(result.allowed)
        self.assertEqual(result.reason, "price_advantage_too_low")

    def test_active_session_does_not_stop_only_because_solar_can_now_fill(self) -> None:
        result = decide(valid_input(active_session=True, forecast_today=100.0))
        self.assertTrue(result.allowed)

    def test_stale_or_invalid_sources_fail_closed(self) -> None:
        result = decide(valid_input(sources_fresh=False))
        self.assertFalse(result.allowed)
        self.assertEqual(result.reason, "sources_stale")


class LearningTests(unittest.TestCase):
    def test_pv_learning_rejects_incomplete_and_outlier_rows(self) -> None:
        learned = learn_pv_correction([1.0, 2.0], actual_kwh=10, forecast_kwh=2, hourly_rows=22)
        self.assertEqual(learned, (1.0, 2.0))
        learned = learn_pv_correction([1.0, 2.0], actual_kwh=20, forecast_kwh=2, hourly_rows=24)
        self.assertEqual(learned, (1.0, 2.0))

    def test_pv_learning_keeps_at_most_fourteen_ratios(self) -> None:
        learned = learn_pv_correction(
            list(range(1, 15)), actual_kwh=2, forecast_kwh=1, hourly_rows=24
        )
        self.assertEqual(len(learned), 14)
        self.assertEqual(learned[-1], 2.0)


if __name__ == "__main__":
    unittest.main()
