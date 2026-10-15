"""Crash boundaries and pending unload remain recoverable, never implicit active."""

import asyncio
from copy import deepcopy
from datetime import UTC, datetime

import pytest

from custom_components.ecoflow_smart_charge.runtime import Runtime
from custom_components.ecoflow_smart_charge.storage import PersistentSessionStore


class Disk:
    def __init__(self):
        self.data = None
        self.cancel = False

    async def async_load(self):
        return deepcopy(self.data)

    async def async_save(self, data):
        if self.cancel:
            raise asyncio.CancelledError()
        self.data = deepcopy(data)


async def setup():
    disk = Disk()
    journal = PersistentSessionStore(disk)
    values = {f"number.slot_{i}": 11 + i for i in range(3)}
    stamps = {e: datetime.now(UTC) for e in values}
    calls = []
    gate = {
        "owned": True,
        "valid": True,
        "master": True,
        "allowed": True,
        "solar_day": "2026-01-04",
    }
    runtime = Runtime(
        "shadow",
        journal,
        lambda e: (values[e], stamps[e]),
        lambda e, v: calls.append((e, v)),
        writers=tuple(values),
        evaluate=lambda: gate.copy(),
        save_comparison=lambda _: None,
    )
    await runtime.async_recalculate()
    await runtime.async_record_comparison({"allowed": True})
    await runtime.async_request_cutover(confirmed=True)
    return runtime, disk, values, stamps, calls, gate


async def test_cancelled_initial_save_sends_zero_commands():
    r, disk, values, _, calls, _ = await setup()
    disk.cancel = True
    with pytest.raises(asyncio.CancelledError):
        await r.async_start(values)
    assert calls == [] and r.journal.record is None


async def test_failed_unload_keeps_explicit_recovery_usable():
    r, _disk, values, _stamps, calls, _ = await setup()
    await r.async_start(values)
    assert not await r.async_close()
    r.mode = "shadow"
    r.authorized = False
    assert not r.closed
    assert not await r.async_confirm_recovery(confirmed=True)
    assert len(calls) >= 6


async def test_restart_of_missing_existing_journal_is_blocked():
    journal = PersistentSessionStore(Disk(), expected_exists=True)
    await journal.async_load()
    assert journal.blocked


async def test_readback_from_before_latest_command_does_not_confirm(freezer):
    r, _disk, values, stamps, calls, _ = await setup()
    originals = dict(values)
    await r.async_start(originals)
    freezer.tick(1)
    for e in values:
        values[e] = 100
        stamps[e] = datetime.now(UTC)
    assert await r.async_retry_charge()
    for e in values:
        values[e] = originals[e]
    # These apparent values were observed BEFORE restore intent was written.
    freezer.tick(1)
    assert not await r.async_restore()
    count = len(calls)
    freezer.tick(31)
    assert not await r.async_restore()
    assert r.journal.record is not None and len(calls) > count


async def test_full_marker_is_saved_before_restore_command_and_survives_clear():
    r, disk, values, stamps, calls, gate = await setup()
    originals = dict(values)
    await r.async_start(originals)
    for e in values:
        values[e] = 100
        stamps[e] = datetime.now(UTC)
    gate["full"] = True

    async def write(e, v):
        assert disk.data["full_marker_day"] == "2026-01-04"
        calls.append((e, v))

    r._write = write
    assert not await r.async_restore()
    for e in values:
        values[e] = originals[e]
        stamps[e] = datetime.now(UTC)
    assert await r.async_restore()
    assert disk.data["full_marker_day"] == "2026-01-04"
    assert disk.data["session"] is None


@pytest.mark.parametrize("operation", ["async_close", "async_set_shadow"])
async def test_stop_persistence_failure_still_revokes_active_authorization(operation):
    r, disk, values, _stamps, calls, _gate = await setup()
    await r.async_start(values)

    async def failed_save(_data):
        raise OSError("disk unavailable")

    disk.async_save = failed_save
    with pytest.raises(OSError):
        await getattr(r, operation)()
    assert r.mode == "shadow"
    assert not r.authorized
    assert r.journal.record is not None
    before = len(calls)
    await r.async_retry_charge()
    assert len(calls) == before
