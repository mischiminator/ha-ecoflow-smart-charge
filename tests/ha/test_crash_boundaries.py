"""Crash boundaries and pending unload remain recoverable."""

import asyncio
from copy import deepcopy
from datetime import UTC, datetime
from types import SimpleNamespace

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
        "valid": True,
        "master": True,
        "allowed": True,
        "solar_day": "2026-01-04",
    }

    async def read(e):
        return values[e], stamps[e]

    async def write(e, v):
        calls.append((e, v))

    async def evaluate():
        return gate.copy()

    runtime = Runtime("active", journal, read, write, writers=tuple(values), evaluate=evaluate)
    return runtime, disk, values, stamps, calls, gate


async def test_cancelled_initial_save_sends_zero_commands():
    r, disk, values, _, calls, _ = await setup()
    disk.cancel = True
    with pytest.raises(asyncio.CancelledError):
        await r._start(values)
    assert calls == [] and r.journal.record is None


async def test_failed_unload_keeps_recovery_usable():
    r, _disk, values, _stamps, calls, _ = await setup()
    await r._start(values)
    assert not await r.async_close()
    assert not r.closed and r.mode == "active"
    assert r.status == "recovery_pending"
    assert not await r._restore()
    assert len(calls) >= 6


async def test_restart_of_missing_existing_journal_is_blocked():
    journal = PersistentSessionStore(Disk(), expected_exists=True)
    await journal.async_load()
    assert journal.blocked


async def test_readback_from_before_latest_command_does_not_confirm(freezer):
    r, _disk, values, stamps, calls, _ = await setup()
    originals = dict(values)
    await r._start(originals)
    freezer.tick(1)
    for e in values:
        values[e] = 100
        stamps[e] = datetime.now(UTC)
    assert await r._execute(r._charge_targets(), restore=False)
    for e in values:
        values[e] = originals[e]
    # These apparent values were observed BEFORE restore intent was written.
    freezer.tick(1)
    assert not await r._restore()
    count = len(calls)
    freezer.tick(31)
    assert not await r._restore()
    assert r.journal.record is not None and len(calls) > count


async def test_full_marker_is_saved_before_restore_command_and_survives_clear():
    r, disk, values, stamps, calls, gate = await setup()
    originals = dict(values)
    await r._start(originals)
    for e in values:
        values[e] = 100
        stamps[e] = datetime.now(UTC)
    gate["full"] = True

    async def write(e, v):
        assert disk.data["full_marker_day"] == "2026-01-04"
        calls.append((e, v))

    r._write = write
    assert not await r._restore()
    for e in values:
        values[e] = originals[e]
        stamps[e] = datetime.now(UTC)
    assert await r._restore()
    assert disk.data["full_marker_day"] == "2026-01-04"
    assert disk.data["session"] is None


class Entries:
    def async_update_entry(self, entry, *, options):
        entry.options = options


@pytest.mark.parametrize(("key", "value"), [("mode", "shadow"), ("master", False)])
async def test_stop_persistence_failure_still_persists_the_stop(key, value):
    r, disk, values, _stamps, calls, _gate = await setup()
    r.entry = SimpleNamespace(options={"master": True, "mode": "active"})
    r.hass = SimpleNamespace(config_entries=Entries())
    await r._start(values)

    async def failed_save(_data):
        raise OSError("disk unavailable")

    disk.async_save = failed_save
    with pytest.raises(OSError):
        await r.async_set_setting(key, value)
    assert r.entry.options[key] == value
    assert r.journal.record is not None
    if key == "mode":
        assert r.mode == "shadow"
        before = len(calls)
        await r._execute(r._charge_targets(), restore=False)
        assert len(calls) == before
