"""Regression tests for fail-closed planning and durable recovery behavior."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from custom_components.ecoflow_smart_charge.planner.core import (
    Battery,
    HourlyProfile,
    PlannerInput,
    PricePoint,
    decide,
)
from custom_components.ecoflow_smart_charge.runtime import Runtime
from custom_components.ecoflow_smart_charge.storage import PersistentSessionStore


class MemoryStore:
    def __init__(self) -> None:
        self.saved: list[dict] = []

    async def async_load(self):
        return self.saved[-1] if self.saved else None

    async def async_save(self, data):
        self.saved.append(data)


def _input(**changes) -> PlannerInput:
    now = datetime(2026, 1, 4, 12, tzinfo=UTC)
    profile = HourlyProfile((2.0,) * 24, (0.0,) * 24, (3,) * 24, True, "ok")
    data = {
        "now": now,
        "prices": tuple(PricePoint(now + timedelta(hours=i), 10.0 if i == 0 else 40.0) for i in range(8)),
        "price_series_updated": now,
        "best_price_window": True,
        "profile": profile,
        "forecast_today": 0.0,
        "forecast_tomorrow": 0.0,
        "pv_correction": 1.0,
        "sunset": now + timedelta(hours=5),
        "batteries": (Battery(50, 3), Battery(50, 3), Battery(50, 3)),
        "capacity_kwh": 2.0,
        "efficiency": 0.85,
        "wear_cost_ct": 2.0,
        "charge_ceiling_ct": 32.0,
        "minimum_net_saving_ct": 3.0,
        "minimum_price_advantage_percent": 25.0,
        "active_session": False,
        "full_marker_for_solar_day": False,
        "sources_fresh": True,
        "protection_mode": True,
    }
    data.update(changes)
    return PlannerInput(**data)


def test_planner_requires_current_price_to_be_in_published_interval() -> None:
    candidate = _input(prices=(PricePoint(_input().now - timedelta(hours=1), 10.0), PricePoint(_input().now, 40.0)))
    result = decide(candidate)
    assert not result.allowed
    assert result.reason == "price_gap"


def test_planner_accepts_current_published_interval_when_now_is_not_on_boundary() -> None:
    now = _input().now + timedelta(minutes=17)
    prices = tuple(PricePoint(_input().now + timedelta(hours=i), 10.0 if i == 0 else 40.0) for i in range(8))
    result = decide(_input(now=now, prices=prices, price_series_updated=now, sunset=now + timedelta(hours=4)))
    assert result.allowed


@pytest.mark.asyncio
async def test_second_start_does_not_overwrite_persisted_individual_reserves() -> None:
    store = PersistentSessionStore(MemoryStore())
    calls: list[tuple[str, float]] = []
    runtime = Runtime("active", store, lambda _entity: 3.0, lambda entity, value: calls.append((entity, value)))
    assert await runtime.async_start({"number.one": 3.0, "number.two": 4.0})
    assert not await runtime.async_start({"number.one": 88.0, "number.two": 99.0})
    assert store.record is not None
    assert store.record.reserves_before == {"number.one": 3.0, "number.two": 4.0}
    assert calls == [("number.one", 100.0), ("number.two", 100.0)]


@pytest.mark.asyncio
async def test_restore_marks_readback_pending_until_a_second_confirmed_read() -> None:
    store = PersistentSessionStore(MemoryStore())
    await store.async_capture_before_command("session", {"number.one": 3.0}, {"number.one": 100.0})
    value = {"number.one": 7.0}
    calls: list[tuple[str, float]] = []
    runtime = Runtime("active", store, lambda entity: value[entity], lambda entity, target: calls.append((entity, target)))
    assert not await runtime.async_restore()
    assert store.record is not None
    assert store.record.phase == "restore_pending"
    assert calls == [("number.one", 3.0)]
    value["number.one"] = 3.0
    assert await runtime.async_restore()
    assert store.record is None
