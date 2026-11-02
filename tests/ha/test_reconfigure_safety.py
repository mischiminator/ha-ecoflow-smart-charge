"""Reconfiguration cannot bypass reserve overlap checks or the safety-state lock."""

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from test_native import mapping

from custom_components.ecoflow_smart_charge.const import DOMAIN


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_reconfigure_rejects_reserve_overlap_and_corrupt_journal(hass):
    data = mapping(hass)
    entry = MockConfigEntry(domain=DOMAIN, data=data)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    other_data = {**data, "reserve_entities": [f"number.other_{i}" for i in range(3)]}
    for entity in other_data["reserve_entities"]:
        hass.states.async_set(entity, "11", {"unit_of_measurement": "%"})
    other = MockConfigEntry(domain=DOMAIN, data=other_data)
    other.add_to_hass(hass)
    flow = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "reconfigure", "entry_id": other.entry_id}
    )
    result = await hass.config_entries.flow.async_configure(flow["flow_id"], user_input=data)
    assert result["type"] == "abort"
    assert result["reason"] == "already_configured"
    entry.runtime_data.journal.blocked = True
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "reconfigure", "entry_id": entry.entry_id}
    )
    assert result["type"] == "abort" and result["reason"] == "recovery_pending"
    entry.runtime_data.journal.blocked = False
    assert await hass.config_entries.async_unload(entry.entry_id)
