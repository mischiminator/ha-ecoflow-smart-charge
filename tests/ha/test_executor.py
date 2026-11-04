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

    async def read(e):
        return values[e], stamps[e]

    async def evaluate():
        return dict(gate)

    async def write(e, v):
        calls.append((e, v))

    runtime = Runtime(
        "active",
        journal,
        read,
        write,
        evaluate=evaluate,
        writers=tuple(values),
    )
    return runtime, disk, values, stamps, calls, gate


@pytest.mark.asyncio
async def test_shadow_mode_sends_no_commands():
    runtime, _, values, _, calls, _ = await rig()
    runtime.mode = "shadow"
    assert not await runtime._start(values)
    await runtime.async_recalculate()
    assert calls == [] and runtime.journal.record is None
    assert runtime.status == "shadow"


@pytest.mark.asyncio
async def test_ack_is_not_readback_and_retry_keeps_originals():
    runtime, _disk, values, stamps, calls, gate = await rig()
    originals = dict(values)
    assert not await runtime._start(originals)
    assert len(calls) == 3
    assert runtime.journal.record.reserves_before == originals
    for e in values:
        values[e] = 100
        stamps[e] = datetime.now(UTC)
    assert await runtime._execute(runtime._charge_targets(), restore=False)
    assert len(calls) == 3
    gate["allowed"] = False
    assert not await runtime._restore()
    assert len(calls) == 6
    for e in values:
        values[e] = originals[e]
        stamps[e] = datetime.now(UTC)
    assert await runtime._restore()
    assert runtime.journal.record is None


@pytest.mark.asyncio
async def test_save_failure_and_closed_gate_send_no_commands():
    runtime, disk, values, _, calls, gate = await rig()
    disk.fail = True
    with pytest.raises(OSError):
        await runtime._start(values)
    assert calls == [] and runtime.journal.record is None
    disk.fail = False
    gate["master"] = False
    assert not await runtime._start(values)
    assert calls == []


@pytest.mark.asyncio
async def test_stale_matching_readback_does_not_clear_restore():
    runtime, _, values, stamps, _calls, _ = await rig()
    originals = dict(values)
    await runtime._start(originals)
    for e in values:
        stamps[e] = datetime.now(UTC) - timedelta(hours=1)
    assert not await runtime._restore()
    assert runtime.journal.record is not None


@pytest.mark.asyncio
async def test_charge_gate_is_rechecked_between_each_device_write():
    runtime, _, values, _, calls, gate = await rig()

    async def write(e, v):
        calls.append((e, v))
        gate["allowed"] = False

    runtime._write = write
    assert not await runtime._start(values)
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
    assert not await runtime._start(values)
    assert len(calls) == 3


async def test_unconfirmed_command_retries_are_rate_limited():
    runtime, _, values, _, calls, _ = await rig()
    await runtime._start(values)
    assert len(calls) == 3
    await runtime._execute(runtime._charge_targets(), restore=False)
    assert len(calls) == 3
    assert runtime.journal.record.phase == "charge_pending"


@pytest.mark.asyncio
async def test_shared_target_is_persisted_and_never_lowers_a_reserve():
    runtime, disk, values, stamps, _calls, gate = await rig()
    gate["targets"] = dict.fromkeys(values, 11.0)
    originals = dict(values)
    assert not await runtime._start(originals)
    # slot_2 keeps its higher original reserve instead of the lower shared target.
    expected = {"number.slot_0": 11.0, "number.slot_1": 11.0, "number.slot_2": 12}
    assert runtime.journal.record.charge_targets == expected
    assert disk.data["session"]["charge_targets"] == expected
    for e, target in expected.items():
        values[e], stamps[e] = target, datetime.now(UTC)
    assert await runtime._execute(runtime._charge_targets(), restore=False)
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
    assert not await runtime._start(dict(values))
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
    assert not await runtime._start(dict(values))
    assert calls == [] and runtime.journal.record is None


@pytest.mark.asyncio
async def test_only_the_master_is_commanded_and_slaves_confirm():
    runtime, _, values, stamps, calls, gate = await rig()
    runtime._leader = lambda: "number.slot_0"
    gate["targets"] = dict.fromkeys(values, 60.0)
    assert not await runtime._start(dict(values))
    assert calls == [("number.slot_0", 60.0)]
    assert {"number.slot_1", "number.slot_2"} <= set(runtime.journal.record.pending_targets)
    # The slaves pick up the synced reserve and report it; the master's own report is not needed.
    for e in ("number.slot_1", "number.slot_2"):
        values[e], stamps[e] = 60.0, datetime.now(UTC)
    assert await runtime._execute(runtime._charge_targets(), restore=False)
    assert runtime.status == "charging" and len(calls) == 1


@pytest.mark.asyncio
async def test_confirmed_charge_holds_without_repeated_reports():
    from dataclasses import replace

    runtime, disk, values, stamps, calls, gate = await rig()
    runtime._leader = lambda: "number.slot_0"
    gate["targets"] = dict.fromkeys(values, 60.0)
    assert not await runtime._start(dict(values))
    record = runtime.journal.record
    past = (datetime.now(UTC) - timedelta(minutes=10)).isoformat()
    runtime.journal.record = replace(
        record, created_at=past, intent_at=dict.fromkeys(record.intent_at, past)
    )
    # The slaves reported the synced value once, five minutes ago, and never again.
    for e in ("number.slot_1", "number.slot_2"):
        values[e], stamps[e] = 60.0, datetime.now(UTC) - timedelta(minutes=5)
    await runtime.async_recalculate()
    assert runtime.status == "charging"
    saved = deepcopy(disk.data)
    await runtime.async_recalculate()
    assert runtime.status == "charging" and len(calls) == 1
    assert disk.data == saved


@pytest.mark.asyncio
async def test_failed_close_finishes_restore_but_never_starts_again():
    runtime, _, values, stamps, calls, _gate = await rig()
    originals = dict(values)
    assert not await runtime._start(dict(values))
    # The restore is sent but not yet confirmed, so the unload fails.
    assert not await runtime.async_close()
    assert runtime.draining and len(calls) == 6
    for e in values:
        values[e], stamps[e] = originals[e], datetime.now(UTC)
    await runtime.async_recalculate()
    assert runtime.journal.record is None
    # The gate is still open, but a failed unload must not start a new session.
    await runtime.async_recalculate()
    assert runtime.journal.record is None and len(calls) == 6


@pytest.mark.asyncio
async def test_single_battery_master_confirms_itself():
    from custom_components.ecoflow_smart_charge.runtime import Runtime

    disk = Disk()
    values, stamps, calls = {"number.solo": 10}, {"number.solo": datetime.now(UTC)}, []

    async def read(e):
        return values[e], stamps[e]

    async def write(e, v):
        calls.append((e, v))

    async def evaluate():
        return dict(gate)

    gate = {"allowed": True, "valid": True, "master": True, "targets": {"number.solo": 50.0}}
    runtime = Runtime(
        "active",
        PersistentSessionStore(disk),
        read,
        write,
        evaluate=evaluate,
        writers=("number.solo",),
        leader=lambda: "number.solo",
    )
    assert not await runtime._start(dict(values))
    values["number.solo"], stamps["number.solo"] = 50.0, datetime.now(UTC)
    assert await runtime._execute(runtime._charge_targets(), restore=False)
    assert calls == [("number.solo", 50.0)]


@pytest.mark.asyncio
async def test_restore_of_a_never_changed_reserve_confirms_after_grace():
    from dataclasses import replace

    runtime, _, values, _stamps, calls, gate = await rig()
    runtime._leader = lambda: "number.slot_0"
    gate["targets"] = dict.fromkeys(values, 60.0)
    assert not await runtime._start(dict(values))
    # The charge command never reached the devices: nothing changed, nothing was reported.
    gate["allowed"] = False
    await runtime.async_recalculate()
    record = runtime.journal.record
    assert record.phase == "restore_pending"
    assert calls[-1] == ("number.slot_0", 10)
    # Within the sync grace the unchanged value is not trusted yet.
    assert not await runtime._restore()
    past = (datetime.now(UTC) - timedelta(seconds=180)).isoformat()
    runtime.journal.record = replace(record, restore_started_at=past)
    assert await runtime._restore()
    assert runtime.journal.record is None and runtime.status == "restored"


@pytest.mark.asyncio
async def test_unchanged_value_never_confirms_a_charge():
    from dataclasses import replace

    runtime, _, values, _stamps, _calls, gate = await rig()
    runtime._leader = lambda: "number.slot_0"
    gate["targets"] = dict.fromkeys(values, 60.0)
    assert not await runtime._start(dict(values))
    record = runtime.journal.record
    past = (datetime.now(UTC) - timedelta(seconds=600)).isoformat()
    runtime.journal.record = replace(record, created_at=past)
    assert not await runtime._execute(runtime._charge_targets(), restore=False)
    assert runtime.journal.record.phase == "charge_pending"


async def test_leader_is_the_single_fresh_battery_with_system_load(hass):
    from custom_components.ecoflow_smart_charge.reader import leader_reserve

    data = {
        "sys_load_entities": ["sensor.load_0", "sensor.load_1", "sensor.load_2"],
        "reserve_entities": ["number.r0", "number.r1", "number.r2"],
    }
    for entity, value in zip(data["sys_load_entities"], ("0", "318", "0"), strict=True):
        hass.states.async_set(entity, value, {"unit_of_measurement": "W"})
    now = datetime.now(UTC)
    assert leader_reserve(hass, data, now) == "number.r1"
    # A stale master is not trusted; neither are two batteries with load.
    assert leader_reserve(hass, data, now + timedelta(seconds=700)) is None
    hass.states.async_set("sensor.load_2", "5", {"unit_of_measurement": "W"})
    assert leader_reserve(hass, data, datetime.now(UTC)) is None
    assert leader_reserve(hass, {"reserve_entities": data["reserve_entities"]}, now) is None
