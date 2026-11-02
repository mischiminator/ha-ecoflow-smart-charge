"""Guarded executor tests with three synthetic devices and independent reports."""

from copy import deepcopy
from datetime import UTC, datetime, timedelta

import pytest

from custom_components.ecoflow_smart_charge.runtime import Runtime
from custom_components.ecoflow_smart_charge.storage import PersistentSessionStore


class Disk:
    def __init__(self):
        self.data = None
        self.fail = False

    async def async_load(self):
        return deepcopy(self.data)

    async def async_save(self, data):
        if self.fail:
            raise OSError("disk full")
        self.data = deepcopy(data)


async def rig():
    disk = Disk()
    journal = PersistentSessionStore(disk)
    values = {f"number.slot_{i}": 10 + i for i in range(3)}
    stamps = {e: datetime.now(UTC) for e in values}
    calls = []
    gate = {
        "allowed": True,
        "valid": True,
        "master": True,
        "full": False,
        "solar_day": "2026-01-04",
    }

    def read(e):
        return (values[e], stamps[e])

    async def write(e, v):
        calls.append((e, v))

    runtime = Runtime(
        "active",
        journal,
        read,
        write,
        evaluate=lambda: dict(gate),
        writers=tuple(values),
    )
    return runtime, disk, values, stamps, calls, gate


@pytest.mark.asyncio
async def test_shadow_mode_sends_no_commands():
    runtime, _, values, _, calls, _ = await rig()
    runtime.mode = "shadow"
    assert not await runtime.async_start(values)
    await runtime.async_recalculate()
    assert calls == [] and runtime.journal.record is None
    assert runtime.status == "shadow"


@pytest.mark.asyncio
async def test_ack_is_not_readback_and_retry_keeps_originals():
    runtime, _disk, values, stamps, calls, gate = await rig()
    originals = dict(values)
    assert not await runtime.async_start(originals)
    assert len(calls) == 3
    assert runtime.journal.record.reserves_before == originals
    for e in values:
        values[e] = 100
        stamps[e] = datetime.now(UTC)
    assert await runtime.async_retry_charge()
    assert len(calls) == 3
    gate["allowed"] = False
    assert not await runtime.async_restore()
    assert len(calls) == 6
    for e in values:
        values[e] = originals[e]
        stamps[e] = datetime.now(UTC)
    assert await runtime.async_restore()
    assert runtime.journal.record is None


@pytest.mark.asyncio
async def test_save_failure_and_closed_gate_send_no_commands():
    runtime, disk, values, _, calls, gate = await rig()
    disk.fail = True
    with pytest.raises(OSError):
        await runtime.async_start(values)
    assert calls == [] and runtime.journal.record is None
    disk.fail = False
    gate["master"] = False
    assert not await runtime.async_start(values)
    assert calls == []


@pytest.mark.asyncio
async def test_stale_matching_readback_does_not_clear_restore():
    runtime, _, values, stamps, _calls, _ = await rig()
    originals = dict(values)
    await runtime.async_start(originals)
    for e in values:
        stamps[e] = datetime.now(UTC) - timedelta(hours=1)
    assert not await runtime.async_restore()
    assert runtime.journal.record is not None


@pytest.mark.asyncio
async def test_charge_gate_is_rechecked_between_each_device_write():
    runtime, _, values, _, calls, gate = await rig()

    async def write(e, v):
        calls.append((e, v))
        gate["allowed"] = False

    runtime._write = write
    assert not await runtime.async_start(values)
    assert len(calls) == 1
    assert runtime.journal.record is not None


@pytest.mark.asyncio
async def test_partial_service_failure_does_not_discard_intent():
    runtime, _, values, _, calls, _ = await rig()

    async def write(e, v):
        calls.append((e, v))
        if e.endswith("1"):
            raise TimeoutError()

    runtime._write = write
    assert not await runtime.async_start(values)
    assert len(calls) == 3


async def test_unconfirmed_command_retries_are_rate_limited():
    runtime, _, values, _, calls, _ = await rig()
    await runtime.async_start(values)
    assert len(calls) == 3
    await runtime.async_retry_charge()
    assert len(calls) == 3
    assert runtime.journal.record.phase == "charge_pending"


@pytest.mark.asyncio
async def test_shared_target_is_persisted_and_never_lowers_a_reserve():
    runtime, disk, values, stamps, _calls, gate = await rig()
    gate["targets"] = dict.fromkeys(values, 11.0)
    originals = dict(values)
    assert not await runtime.async_start(originals)
    # slot_2 keeps its higher original reserve instead of the lower shared target.
    expected = {"number.slot_0": 11.0, "number.slot_1": 11.0, "number.slot_2": 12}
    assert runtime.journal.record.charge_targets == expected
    assert disk.data["session"]["charge_targets"] == expected
    for e, target in expected.items():
        values[e], stamps[e] = target, datetime.now(UTC)
    assert await runtime.async_retry_charge()
    assert runtime.status == "charging"
    # The window ends before the batteries are full: restore, but no solar-day marker,
    # so a later cheap window (e.g. at noon) may still top up.
    gate["allowed"] = False
    await runtime.async_recalculate()
    assert runtime.journal.record.phase == "restore_pending"
    assert runtime.journal.full_marker_day is None


@pytest.mark.asyncio
async def test_running_session_follows_forecast_with_hysteresis():
    runtime, disk, values, _stamps, calls, gate = await rig()
    gate["targets"] = dict.fromkeys(values, 60.0)
    assert not await runtime.async_start(dict(values))
    calls.clear()
    # A one-point forecast wobble is not worth a device command.
    gate["targets"] = dict.fromkeys(values, 61.0)
    await runtime.async_recalculate()
    assert set(runtime.journal.record.charge_targets.values()) == {60.0}
    # A real change raises (or lowers) the shared reserve on every battery.
    gate["targets"] = dict.fromkeys(values, 70.0)
    await runtime.async_recalculate()
    assert set(runtime.journal.record.charge_targets.values()) == {70.0}
    assert sorted(calls) == [(e, 70.0) for e in sorted(values)]
    assert disk.data["session"]["charge_targets"] == dict.fromkeys(values, 70.0)
    calls.clear()
    gate["targets"] = dict.fromkeys(values, 40.0)
    await runtime.async_recalculate()
    assert sorted(calls) == [(e, 40.0) for e in sorted(values)]


@pytest.mark.asyncio
async def test_no_session_when_targets_do_not_exceed_original_reserves():
    runtime, _, values, _, calls, gate = await rig()
    gate["targets"] = dict.fromkeys(values, 5.0)
    assert not await runtime.async_start(dict(values))
    assert calls == [] and runtime.journal.record is None
