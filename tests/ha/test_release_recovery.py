"""Acceptance probes for durable crash boundaries and full-marker save failure."""

import asyncio
from datetime import UTC, datetime

import pytest
from test_crash_boundaries import setup

from custom_components.ecoflow_smart_charge.runtime import Runtime
from custom_components.ecoflow_smart_charge.storage import PersistentSessionStore


@pytest.mark.parametrize("save_number,prior_writes", [(1, 0), (2, 0), (3, 0), (4, 1), (5, 2)])
async def test_restart_after_each_durable_charge_boundary(save_number, prior_writes, freezer):
    runtime, disk, values, stamps, calls, gate = await setup()
    originals = dict(values)
    save = disk.async_save
    count = 0

    async def crash_after_save(data):
        nonlocal count
        await save(data)
        count += 1
        if count == save_number:
            raise asyncio.CancelledError()

    disk.async_save = crash_after_save
    with pytest.raises(asyncio.CancelledError):
        await runtime._start(values)
    assert len(calls) == prior_writes
    assert disk.data["session"]["reserves_before"] == originals
    disk.async_save = save
    journal = PersistentSessionStore(disk, expected_exists=True)
    await journal.async_load()
    gate["allowed"] = False

    async def read(e):
        return values[e], stamps[e]

    async def write(e, v):
        calls.append((e, v))

    async def evaluate():
        return gate.copy()

    def restart(mode):
        return Runtime(mode, journal, read, write, writers=tuple(values), evaluate=evaluate)

    # A shadow restart keeps the session pending and sends nothing.
    shadow = restart("shadow")
    await shadow.async_recalculate()
    assert not await shadow._restore()
    assert shadow.status == "recovery_pending"
    assert len(calls) == prior_writes
    # An active restart restores the saved originals once charging is no longer allowed.
    restarted = restart("active")
    await restarted.async_recalculate()
    assert len(calls) == prior_writes + 3
    # Only two newly reported originals are insufficient; retry only the third.
    freezer.tick(1)
    for entity in list(values)[:2]:
        stamps[entity] = datetime.now(UTC)
    assert not await restarted._restore()
    assert journal.record is not None
    assert len(calls) == prior_writes + 3  # retry is rate-limited
    freezer.tick(31)
    assert not await restarted._restore()
    assert calls[-1] == (list(values)[2], originals[list(values)[2]])
    assert len(calls) == prior_writes + 4
    freezer.tick(1)
    stamps[list(values)[2]] = datetime.now(UTC)
    assert await restarted._restore()
    assert journal.record is None and disk.data["session"] is None


async def test_full_marker_save_failure_prevents_restore_commands():
    runtime, disk, values, _stamps, calls, gate = await setup()
    await runtime._start(values)
    prior = len(calls)
    gate["full"] = True
    save = disk.async_save

    async def fail_marker(data):
        if data["full_marker_day"] is not None:
            raise OSError("synthetic durable marker failure")
        await save(data)

    disk.async_save = fail_marker
    with pytest.raises(OSError):
        await runtime._restore()
    assert len(calls) == prior
    assert runtime.journal.record is not None
    assert disk.data["full_marker_day"] is None
