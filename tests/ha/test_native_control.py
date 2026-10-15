"""Native services drive the actual source reader/core/journal/executor chain."""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from homeassistant.core import SupportsResponse
from pytest_homeassistant_custom_component.common import MockConfigEntry
from test_source_pipeline import data_states

from custom_components.ecoflow_smart_charge.const import DOMAIN


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_native_cutover_conflict_and_verified_restoration(hass, freezer):
    freezer.move_to("2026-01-04T20:01:01+00:00")
    now = datetime.now(UTC)
    data = data_states(hass, now)
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
        # The safety capture and per-target intent exist before transport invocation.
        record = entry.runtime_data.journal.record
        assert record.reserves_before == {e: 13.0 for e in data["reserve_entities"]}
        assert call.data["entity_id"] in record.command_ids
        calls.append(dict(call.data))

    entry = MockConfigEntry(domain=DOMAIN, data=data, options={"master": True})
    entry.add_to_hass(hass)
    with patch("custom_components.ecoflow_smart_charge.reader.read_statistics", return_value=rows):
        assert await hass.config_entries.async_setup(entry.entry_id)
        hass.services.async_register("number", "set_value", write)
        target = {"config_entry_id": entry.entry_id}
        await hass.services.async_call(DOMAIN, "recalculate", target, blocking=True)
        runtime = entry.runtime_data
        gate = runtime.last_snapshot
        assert gate["valid"] and gate["allowed"] and calls == []
        expected = {
            k: gate[k] for k in ("allowed", "reason", "advantage", "net_saving", "profile_valid")
        }
        await hass.services.async_call(
            DOMAIN, "record_shadow_comparison", {**target, "expected": expected}, blocking=True
        )
        await hass.services.async_call(
            DOMAIN, "request_cutover", {**target, "confirmed": True}, blocking=True
        )
        await hass.services.async_call(DOMAIN, "recalculate", target, blocking=True)
        assert len(calls) == 3 and runtime.journal.record
        # A configured competing writer becoming enabled must prevent ANY further command.
        hass.states.async_set("automation.legacy", "on")
        await hass.services.async_call(DOMAIN, "recalculate", target, blocking=True)
        assert len(calls) == 3
        hass.states.async_set("automation.legacy", "off")
        await runtime.async_set_shadow()
        assert runtime.mode == "shadow" and runtime.journal.record
        assert len(calls) == 6  # safe restoration under still-active exclusive ownership
        freezer.tick(1)
        for entity in data["reserve_entities"]:
            hass.states.async_set(entity, "13", {"unit_of_measurement": "%"})
        await hass.services.async_call(
            DOMAIN, "confirm_recovery", {**target, "confirmed": True}, blocking=True
        )
        assert runtime.journal.record is None and len(calls) == 6
        assert await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()
        assert runtime.closed and not runtime.cancels and not runtime.listeners
