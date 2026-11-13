"""Native options preserve runtime ownership; real disable/unload remains guarded."""

import pytest
from homeassistant.config_entries import ConfigEntryDisabler
from pytest_homeassistant_custom_component.common import MockConfigEntry
from test_native import mapping

from custom_components.ecoflow_smart_charge.const import DOMAIN


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_options_flow_updates_in_place_and_disable_cleans_resources(hass):
    entry = MockConfigEntry(domain=DOMAIN, data=mapping(hass))
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    original = entry.runtime_data
    flow = await hass.config_entries.options.async_init(entry.entry_id)
    flow = await hass.config_entries.options.async_configure(
        flow["flow_id"], {"settings_mode": "advanced"}
    )
    result = await hass.config_entries.options.async_configure(
        flow["flow_id"],
        user_input={"master": True, "mode": "shadow", "minimum_price_advantage_percent": 26.0},
    )
    assert result["type"] == "create_entry"
    await hass.async_block_till_done()
    assert not original.closed and original.cancels and original.listeners
    assert entry.runtime_data is original
    assert entry.runtime_data.mode == "shadow"
    assert entry.options["minimum_price_advantage_percent"] == 26.0
    runtime = entry.runtime_data
    await hass.config_entries.async_set_disabled_by(entry.entry_id, ConfigEntryDisabler.USER)
    await hass.async_block_till_done()
    assert runtime.closed and not runtime.cancels and not runtime.listeners
    assert entry.disabled_by is ConfigEntryDisabler.USER


async def save_options(hass, entry, settings_mode, values):
    flow = await hass.config_entries.options.async_init(entry.entry_id)
    form = await hass.config_entries.options.async_configure(
        flow["flow_id"], {"settings_mode": settings_mode}
    )
    result = await hass.config_entries.options.async_configure(form["flow_id"], values)
    assert result["type"] == "create_entry"
    await hass.async_block_till_done()


@pytest.fixture
async def active_controller(hass, freezer, enable_custom_integrations):
    from datetime import UTC, datetime, timedelta
    from unittest.mock import patch

    from homeassistant.core import SupportsResponse
    from test_source_pipeline import data_states

    freezer.move_to("2026-01-04T20:01:01+00:00")
    now = datetime.now(UTC)
    data = data_states(hass, now)
    rows = [
        {
            "start": (now - timedelta(days=d)).replace(hour=h, minute=0, second=0, microsecond=0),
            "grid": 2.0,
            "pv": 0.0,
            "charges": (0.0,) * 3,
            "discharges": (0.0,) * 3,
        }
        for d in range(1, 15)
        for h in range(24)
    ]

    start = now.replace(minute=0, second=0, microsecond=0)

    async def prices(call):
        return {
            "prices": {
                "Chosen": [
                    {
                        "start_time": (start + timedelta(minutes=15 * i)).isoformat(),
                        "price": 0.1 if i == 0 else 0.5,
                    }
                    for i in range(192)
                ]
            }
        }

    hass.services.async_register(
        "tibber", "get_prices", prices, supports_response=SupportsResponse.ONLY
    )
    calls = []

    async def write(call):
        # Transport ACK deliberately does not update telemetry.
        calls.append(dict(call.data))

    entry = MockConfigEntry(
        domain=DOMAIN,
        data=data,
        options={"master": True, "mode": "active", "settings_mode": "simple"},
    )
    entry.add_to_hass(hass)
    with patch("custom_components.ecoflow_smart_charge.reader.read_statistics", return_value=rows):
        assert await hass.config_entries.async_setup(entry.entry_id)
        hass.services.async_register("number", "set_value", write)
        await entry.runtime_data.async_recalculate()
        assert entry.runtime_data.journal.record is not None and len(calls) == 3
        yield entry, calls


@pytest.mark.parametrize(
    "settings_mode,values",
    [
        ("simple", {"charging_policy": "protect_battery"}),
        ("advanced", {"minimum_net_saving_ct": 4.2}),
        ("simple", {}),
    ],
)
async def test_native_settings_save_preserves_session_and_next_window(
    hass, freezer, active_controller, settings_mode, values
):
    entry, calls = active_controller
    runtime = entry.runtime_data
    if settings_mode == "simple" and not values:
        await runtime.async_set_setting("settings_mode", "advanced")
    record = runtime.journal.record
    timers = tuple(runtime.cancels)
    writers = runtime.writers
    originals = dict(record.reserves_before)
    await save_options(hass, entry, settings_mode, values)
    assert entry.runtime_data is runtime
    assert not runtime.draining and not runtime.closed
    assert tuple(runtime.cancels) == timers and runtime.writers == writers
    assert runtime.journal.record is record
    assert runtime.applied_options == dict(entry.options)
    assert len(calls) == 3  # Saving must not issue restore commands.

    # A real window end restores, retains the journal until delayed readback,
    # then permits a new window without restarting the entry.
    freezer.tick(1)
    hass.states.async_set(entry.data["price_window_entity"], "off")
    await hass.async_block_till_done()
    assert runtime.journal.record.phase == "restore_pending" and len(calls) == 6
    freezer.tick(1)
    for entity, value in originals.items():
        hass.states.async_set(entity, str(value), {"unit_of_measurement": "%"})
    await hass.async_block_till_done()
    assert runtime.journal.record is None
    freezer.tick(1)
    hass.states.async_set(entry.data["price_window_entity"], "on")
    await hass.async_block_till_done()
    assert runtime.journal.record is not None and len(calls) == 9
    assert runtime.journal.record.session_id != record.session_id
    assert runtime.journal.record.reserves_before == originals

    await runtime.async_set_setting("master", False)
    freezer.tick(1)
    for entity, value in originals.items():
        hass.states.async_set(entity, str(value), {"unit_of_measurement": "%"})
    await hass.async_block_till_done()
    assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.parametrize("stop", [{"master": False}, {"mode": "shadow"}])
async def test_native_stop_preserves_delayed_restore_contract(
    hass, freezer, active_controller, stop
):
    entry, calls = active_controller
    runtime = entry.runtime_data
    originals = dict(runtime.journal.record.reserves_before)
    await save_options(hass, entry, "simple", stop)
    assert entry.runtime_data is runtime and not runtime.draining
    assert len(calls) == 6 and runtime.journal.record.phase == "restore_pending"
    assert runtime.mode == stop.get("mode", "active")
    freezer.tick(1)
    for entity, value in originals.items():
        hass.states.async_set(entity, str(value), {"unit_of_measurement": "%"})
    await hass.async_block_till_done()
    if stop.get("mode") == "shadow":
        assert runtime.journal.record is not None and len(calls) == 6
        await save_options(hass, entry, "simple", {"master": False, "mode": "active"})
        await runtime.async_recalculate()
    assert runtime.journal.record is None and len(calls) == 6
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_native_policy_edit_does_not_revive_failed_unload(hass, freezer, active_controller):
    entry, calls = active_controller
    runtime = entry.runtime_data
    originals = dict(runtime.journal.record.reserves_before)
    assert not await hass.config_entries.async_unload(entry.entry_id)
    assert runtime.draining
    await save_options(hass, entry, "simple", {"charging_policy": "save_more"})
    assert runtime.draining and entry.runtime_data is runtime
    freezer.tick(1)
    for entity, value in originals.items():
        hass.states.async_set(entity, str(value), {"unit_of_measurement": "%"})
    await hass.async_block_till_done()
    await runtime.async_recalculate()
    assert runtime.draining and runtime.journal.record is None and len(calls) == 6
    # HA marks FAILED_UNLOAD non-recoverable; do not pretend a UI edit repairs it.
    assert await runtime.async_close()


async def test_queued_entity_write_does_not_mask_native_mode_stop(hass, active_controller):
    import asyncio

    entry, calls = active_controller
    runtime = entry.runtime_data
    flow = await hass.config_entries.options.async_init(entry.entry_id)
    form = await hass.config_entries.options.async_configure(
        flow["flow_id"], {"settings_mode": "simple"}
    )
    async with runtime._lock:
        entity_write = asyncio.create_task(runtime.async_set_setting("charge_ceiling_ct", 29.3))
        await asyncio.sleep(0)  # Queue entity write ahead of the native listener.
        result = await hass.config_entries.options.async_configure(
            form["flow_id"], {"mode": "shadow"}
        )
        assert result["type"] == "create_entry"
        assert runtime.mode == "active" and len(calls) == 3
    await entity_write
    await hass.async_block_till_done()
    assert runtime.mode == "shadow" and len(calls) == 6
    assert runtime.journal.record.phase == "restore_pending"
    assert runtime.applied_options == dict(entry.options)
    assert entry.options["charge_ceiling_ct"] == 29.3


async def persist_options(hass, entry, settings_mode, values):
    """Save through HA without waiting for a suspended runtime listener."""
    flow = await hass.config_entries.options.async_init(entry.entry_id)
    form = await hass.config_entries.options.async_configure(
        flow["flow_id"], {"settings_mode": settings_mode}
    )
    result = await hass.config_entries.options.async_configure(form["flow_id"], values)
    assert result["type"] == "create_entry"


@pytest.mark.parametrize("cancel_restore", [False, True])
async def test_entity_stop_rebases_native_save_during_transport_restore(
    hass, active_controller, cancel_restore
):
    import asyncio

    entry, calls = active_controller
    runtime = entry.runtime_data
    entered, release = asyncio.Event(), asyncio.Event()
    original_write = runtime._write

    async def suspended_write(entity, value):
        entered.set()
        await release.wait()
        await original_write(entity, value)

    runtime._write = suspended_write
    entity_write = asyncio.create_task(runtime.async_set_setting("master", False))
    try:
        await asyncio.wait_for(entered.wait(), 5)
        await persist_options(
            hass, entry, "simple", {"mode": "shadow", "charging_policy": "protect_battery"}
        )
        assert entry.options["mode"] == "shadow"
        assert runtime.mode == "active"
        if cancel_restore:
            entity_write.cancel()
    finally:
        release.set()
        if cancel_restore:
            with pytest.raises(asyncio.CancelledError):
                await entity_write
        else:
            await entity_write
    await hass.async_block_till_done()
    expected = {
        "master": False,
        "mode": "shadow",
        "settings_mode": "simple",
        "charging_policy": "protect_battery",
    }
    assert dict(entry.options) == expected
    assert runtime.applied_options == expected
    assert runtime.mode == "shadow" and not runtime.draining
    assert runtime.journal.record.phase == "restore_pending"
    expected_calls = 5 if cancel_restore else 6
    assert len(calls) == expected_calls
    originals = runtime.journal.record.reserves_before
    assert all(call["value"] == originals[call["entity_id"]] for call in calls[3:])
    await runtime.async_recalculate()
    assert len(calls) == expected_calls


@pytest.mark.parametrize(
    "first,second",
    [
        ({"master": False}, {"mode": "shadow", "charging_policy": "protect_battery"}),
        ({"mode": "shadow"}, {"mode": "active", "master": False}),
    ],
)
async def test_native_listener_reconciles_edits_during_its_restore(
    hass, active_controller, first, second, monkeypatch
):
    import asyncio

    entry, calls = active_controller
    runtime = entry.runtime_data
    entered, release = asyncio.Event(), asyncio.Event()
    original_write = runtime._write
    original_apply = runtime.async_apply_options
    completed = []

    async def suspended_write(entity, value):
        entered.set()
        await release.wait()
        await original_write(entity, value)

    async def observed_apply():
        await original_apply()
        completed.append((runtime.mode, dict(runtime.applied_options)))

    runtime._write = suspended_write
    monkeypatch.setattr(runtime, "async_apply_options", observed_apply)
    await persist_options(hass, entry, "simple", first)
    try:
        await asyncio.wait_for(entered.wait(), 5)
        await persist_options(hass, entry, "simple", second)
        expected = dict(entry.options)
        assert runtime.applied_options != expected
    finally:
        release.set()
    await hass.async_block_till_done()
    # Check the first listener's own settled result, not just the later queued
    # listener repairing it after the lock was released.
    assert completed[0] == (expected["mode"], expected)
    assert runtime.mode == expected["mode"]
    assert runtime.applied_options == dict(entry.options) == expected
    assert runtime.journal.record.phase == "restore_pending" and not runtime.draining
    assert len(calls) == 6
    await runtime.async_recalculate()
    assert len(calls) == 6
