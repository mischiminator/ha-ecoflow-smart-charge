"""Real Home Assistant lifecycle/config-flow regression coverage."""
from __future__ import annotations

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ecoflow_smart_charge.const import DOMAIN


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_entry_setup_is_shadow_by_default_and_registers_targeted_services(hass) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test controller",
        data={
            "name": "Test controller",
            "grid_energy_entity": "sensor.required_grid",
            "price_entity": "sensor.prices",
            "price_window_entity": "binary_sensor.window",
            "pv_entity": "sensor.pv",
            "soc_entities": ["sensor.soc_1", "sensor.soc_2", "sensor.soc_3"],
            "reserve_entities": ["number.reserve_1", "number.reserve_2", "number.reserve_3"],
            "self_powered_entities": ["switch.self_1", "switch.self_2", "switch.self_3"],
            "operating_mode_entities": ["select.mode_1", "select.mode_2", "select.mode_3"],
        },
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    runtime = entry.runtime_data
    assert runtime.mode == "shadow"
    assert runtime.status == "shadow"
    assert hass.services.has_service(DOMAIN, "recalculate")
    assert hass.services.has_service(DOMAIN, "request_cutover")
    assert hass.services.has_service(DOMAIN, "confirm_recovery")

    await hass.services.async_call(
        DOMAIN, "recalculate", {"config_entry_id": entry.entry_id}, blocking=True
    )
    assert runtime.status == "shadow_recalculated"

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
