"""Configured writer ownership must remain fresh across source awaits."""

import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from homeassistant.core import SupportsResponse
from pytest_homeassistant_custom_component.common import MockConfigEntry
from test_executor import rig
from test_source_pipeline import data_states

from custom_components.ecoflow_smart_charge.reader import SourceReader
from custom_components.ecoflow_smart_charge.storage import PersistentSessionStore


@pytest.mark.parametrize("conflicting_state", ["on", "unavailable", None])
async def test_restore_rejects_writer_change_inside_post_intent_refresh(hass, conflicting_state):
    runtime, _, values, _, calls, _ = await rig()
    await runtime.async_start(values)
    calls.clear()
    hass.states.async_set("automation.legacy", "off")
    entry = MockConfigEntry(
        domain="ecoflow_smart_charge",
        data={
            "legacy_writer_entities": ["automation.legacy"],
            "soc_entities": [],
            "grid_energy_entity": "sensor.grid",
            "pv_entity": "sensor.pv",
            "charge_energy_entities": ["sensor.c1", "sensor.c2", "sensor.c3"],
            "discharge_energy_entities": ["sensor.d1", "sensor.d2", "sensor.d3"],
        },
        options={"master": True},
    )
    reader = SourceReader(hass, entry, runtime.journal)
    refreshes = 0

    async def statistics(*_args):
        nonlocal refreshes
        refreshes += 1
        if refreshes == 3:  # final gate, after the restore intent was persisted
            if conflicting_state is None:
                hass.states.async_remove("automation.legacy")
            else:
                hass.states.async_set("automation.legacy", conflicting_state)
        await asyncio.sleep(0)
        raise ValueError("statistics unavailable after yielding")

    runtime._evaluate = reader.refresh
    with patch("custom_components.ecoflow_smart_charge.reader.read_statistics", statistics):
        assert not await runtime.async_restore()
    assert refreshes == 3
    assert calls == []
    assert runtime.journal.record is not None
    assert runtime.journal.record.phase == "restore_pending"
    assert runtime.last_snapshot["owned"] is False


@pytest.mark.parametrize("source_fails", [False, True])
async def test_ownership_is_current_after_successful_or_failed_price_await(
    hass, freezer, source_fails
):
    freezer.move_to("2026-01-04T14:00:00+00:00")
    now = datetime.now(UTC)
    data = data_states(hass, now)
    reader = SourceReader(
        hass,
        MockConfigEntry(domain="ecoflow_smart_charge", data=data, options={"master": True}),
        PersistentSessionStore(None),
    )
    rows = [
        {
            "start": (now - timedelta(days=d)).replace(hour=h, minute=0, second=0, microsecond=0),
            "grid": 2.0,
            "pv": 0.0,
            "charges": (0.0, 0.0, 0.0),
            "discharges": (0.0, 0.0, 0.0),
        }
        for d in range(1, 15)
        for h in range(24)
    ]
    start = datetime.fromtimestamp(int(now.timestamp() // 900) * 900, UTC)

    async def prices(_call):
        hass.states.async_set("automation.legacy", "on")
        await asyncio.sleep(0)
        if source_fails:
            raise ValueError("price source failed after yielding")
        return {
            "prices": {
                "Chosen": [
                    {
                        "start_time": (start + timedelta(minutes=15 * i)).isoformat(),
                        "price": 0.10 if i == 0 else 0.50,
                    }
                    for i in range(192)
                ]
            }
        }

    hass.services.async_register(
        "tibber", "get_prices", prices, supports_response=SupportsResponse.ONLY
    )
    with patch("custom_components.ecoflow_smart_charge.reader.read_statistics", return_value=rows):
        gate = await reader.refresh()
    assert gate["valid"] is not source_fails
    assert gate["owned"] is False
