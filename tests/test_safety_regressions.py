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
        "prices": tuple(
            PricePoint(now + timedelta(minutes=15 * i), 10.0 if i == 0 else 40.0) for i in range(64)
        ),
        "current_price_ct": 10.0,
        "below_horizon": False,
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
        "protection_mode": True,
    }
    data.update(changes)
    return PlannerInput(**data)


def test_planner_requires_current_price_to_be_in_published_interval() -> None:
    candidate = _input(
        prices=(PricePoint(_input().now - timedelta(hours=1), 10.0), PricePoint(_input().now, 40.0))
    )
    result = decide(candidate)
    assert not result.allowed
    assert result.reason == "current_price_mismatch"


def test_planner_accepts_current_published_interval_when_now_is_not_on_boundary() -> None:
    now = _input().now + timedelta(minutes=2)
    prices = _input().prices
    result = decide(
        _input(now=now, prices=prices, price_series_updated=now, sunset=now + timedelta(hours=4))
    )
    assert result.allowed


@pytest.mark.asyncio
async def test_second_start_does_not_overwrite_persisted_individual_reserves() -> None:
    store = PersistentSessionStore(MemoryStore())
    calls: list[tuple[str, float]] = []

    async def write(entity, value):
        calls.append((entity, value))

    runtime = Runtime("active", store, lambda _entity: 3.0, write)
    await store.async_capture_before_command(
        "persisted",
        {"number.one": 3.0, "number.two": 4.0},
        {"number.one": 100.0, "number.two": 100.0},
    )
    assert not await runtime._start({"number.one": 88.0, "number.two": 99.0})
    assert store.record is not None
    assert store.record.reserves_before == {"number.one": 3.0, "number.two": 4.0}
    assert calls == []


@pytest.mark.asyncio
async def test_restore_marks_readback_pending_until_a_second_confirmed_read() -> None:
    store = PersistentSessionStore(MemoryStore())
    originals = {"number.one": 3.0, "number.two": 4.0, "number.three": 5.0}
    await store.async_capture_before_command("session", originals, {e: 100.0 for e in originals})
    values = {e: 100.0 for e in originals}
    stamps = {e: datetime.now(UTC) for e in originals}
    calls = []

    async def read(e):
        return values[e], stamps[e]

    async def write(e, v):
        calls.append((e, v))

    async def evaluate():
        return {}

    runtime = Runtime(
        "active",
        store,
        read,
        write,
        writers=tuple(originals),
        evaluate=evaluate,
    )
    assert not await runtime._restore()
    assert store.record is not None
    assert store.record.phase == "restore_pending"
    assert len(calls) == 3
    values.update(originals)
    stamps.update({e: datetime.now(UTC) for e in originals})
    assert await runtime._restore()
    assert store.record is None and runtime.status == "restored"
