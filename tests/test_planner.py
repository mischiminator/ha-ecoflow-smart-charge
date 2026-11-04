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

    def test_active_session_holds_once_solar_can_fill_the_rest(self) -> None:
        batteries = (Battery(soc=61.7, reserve=3),) * 3
        result = decide(
            valid_input(
                active_session=True,
                batteries=batteries,
                profile=solar_profile(),
                forecast_today=100.0,
            )
        )
        self.assertTrue(result.allowed)
        self.assertEqual(result.reason, "target_reached")
        # Hold the stored energy for the expensive hours instead of discharging now.
        self.assertEqual(result.target_soc, 61.0)
        ended = decide(
            valid_input(
                active_session=True,
                batteries=batteries,
                profile=solar_profile(),
                forecast_today=100.0,
                best_price_window=False,
            )
        )
        self.assertEqual(ended.reason, "outside_best_price_window")


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


class BatteryCountTests(unittest.TestCase):
    def test_any_battery_count_plans_and_scales_missing_energy(self) -> None:
        one = decide(valid_input(batteries=(Battery(soc=50, reserve=3),)))
        four = decide(valid_input(batteries=(Battery(soc=50, reserve=3),) * 4))
        self.assertNotEqual(one.reason, "battery_data_invalid")
        self.assertNotEqual(four.reason, "battery_data_invalid")
        self.assertAlmostEqual(four.missing_energy_kwh, 4 * one.missing_energy_kwh)
        self.assertEqual(decide(valid_input(batteries=())).reason, "battery_data_invalid")

    def test_profile_accepts_one_battery_rows_and_rejects_mismatched_lists(self) -> None:
        rows = [{**r, "charges": (0.3,), "discharges": (0.6,)} for r in complete_rows()]
        single = build_hourly_profile(rows)
        self.assertTrue(single.valid)
        three = build_hourly_profile(complete_rows())
        for a, b in zip(single.house_by_hour, three.house_by_hour, strict=True):
            self.assertAlmostEqual(a, b)
        broken = [{**r, "discharges": (0.6, 0.0)} for r in rows]
        self.assertFalse(build_hourly_profile(broken).valid)


class SolarTargetTests(unittest.TestCase):
    def test_grid_charges_only_the_gap_that_pv_surplus_cannot_fill(self) -> None:
        batteries = (Battery(soc=20, reserve=3, capacity_kwh=1.92),) * 2 + (
            Battery(soc=50, reserve=3, capacity_kwh=3.84),
        )
        none = decide(valid_input(batteries=batteries))
        self.assertEqual(none.target_soc, 100.0)
        self.assertAlmostEqual(none.grid_kwh, none.missing_energy_kwh)
        self.assertAlmostEqual(none.missing_energy_kwh, 2 * 1.92 * 0.8 + 3.84 * 0.5)
        some = decide(valid_input(batteries=batteries, profile=solar_profile(), forecast_today=12))
        self.assertTrue(0 < some.solar_surplus_kwh < some.missing_energy_kwh)
        self.assertAlmostEqual(some.grid_kwh, some.missing_energy_kwh - some.solar_surplus_kwh)
        # One shared reserve: its grid charge covers the gap, one percent less would not.
        target = some.target_soc
        self.assertEqual(target, int(target))
        self.assertTrue(50 < target < 100)

        def charged(level):
            return sum((b.capacity_kwh or 0) * max(level - b.soc, 0) / 100 for b in batteries)

        self.assertGreaterEqual(charged(target), some.grid_kwh)
        self.assertLess(charged(target - 1), some.grid_kwh)
        self.assertLess(some.target_ac_kwh, none.target_ac_kwh)

    def test_shared_target_can_leave_fuller_batteries_to_pv(self) -> None:
        batteries = (Battery(10, 3, 1.92), Battery(90, 3, 1.92))
        result = decide(
            valid_input(batteries=batteries, profile=solar_profile(), forecast_today=12)
        )
        self.assertTrue(result.allowed)
        self.assertLess(result.target_soc, 90)
        self.assertGreater(result.target_soc, 10)

    def test_unknown_model_capacity_uses_configured_fallback(self) -> None:
        mixed = decide(
            valid_input(
                batteries=(Battery(50, 3, 3.84), Battery(50, 3)),
                capacity_kwh=1.0,
            )
        )
        self.assertAlmostEqual(mixed.missing_energy_kwh, 3.84 * 0.5 + 1.0 * 0.5)
        bad = decide(valid_input(batteries=(Battery(50, 3, 0.0),)))
        self.assertEqual(bad.reason, "battery_data_invalid")


def solar_profile():
    rows = [{**r, "pv": 0.6 if 8 <= r["start"].hour <= 16 else 0.0} for r in complete_rows()]
    return build_hourly_profile(rows)


class MiddayWindowTests(unittest.TestCase):
    """Tomorrow's prices appear around 13:00; a late-morning window only knows today's."""

    def midday(self, batteries):
        now = datetime(2026, 1, 4, 11, tzinfo=UTC)
        quarters = int((datetime(2026, 1, 5, tzinfo=UTC) - now).total_seconds() // 900)
        prices = tuple(
            PricePoint(now + timedelta(minutes=15 * i), 10.0 if i < 8 else 40.0)
            for i in range(quarters)
        )
        return decide(
            valid_input(
                now=now,
                price_series_updated=now,
                sunset=now + timedelta(hours=5),
                prices=prices,
                batteries=batteries,
                profile=solar_profile(),
                forecast_today=4,
            )
        )

    def test_today_prices_suffice_when_evening_covers_the_charge(self) -> None:
        result = self.midday((Battery(20, 3, 1.92),) * 3)
        self.assertTrue(result.allowed)
        self.assertEqual(result.coverage_fraction, 1.0)

    def test_consumption_after_last_published_price_is_not_counted(self) -> None:
        result = self.midday((Battery(5, 3, 3.84),) * 10)
        self.assertNotEqual(result.reason, "price_gap")
        self.assertLess(result.coverage_fraction, 1.0)
        self.assertLess(result.coverage_kwh, result.target_ac_kwh)
