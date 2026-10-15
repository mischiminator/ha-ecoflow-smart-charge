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
        "owned": True,
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
        "shadow",
        journal,
        read,
        write,
        evaluate=lambda: dict(gate),
        writers=tuple(values),
        save_comparison=lambda _: None,
    )
    await runtime.async_recalculate()
    await runtime.async_record_comparison({"allowed": True})
    await runtime.async_request_cutover(confirmed=True, commissioning_confirmed=True)
    return runtime, disk, values, stamps, calls, gate


@pytest.mark.asyncio
async def test_no_cutover_without_confirmation_or_comparison():
    runtime, _, _, _, calls, _ = await rig()
    runtime.mode = "shadow"
    runtime.comparison = None
    with pytest.raises(ValueError):
        await runtime.async_request_cutover(confirmed=True, commissioning_confirmed=True)
    assert calls == []


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
async def test_save_failure_and_conflict_send_no_commands():
    runtime, disk, values, _, calls, gate = await rig()
    disk.fail = True
    with pytest.raises(OSError):
        await runtime.async_start(values)
    assert calls == [] and runtime.journal.record is None
    disk.fail = False
    gate["owned"] = False
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
async def test_conflict_is_rechecked_between_each_device_write():
    runtime, _, values, _, calls, gate = await rig()

    async def write(e, v):
        calls.append((e, v))
        gate["owned"] = False

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
