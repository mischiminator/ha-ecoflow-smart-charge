"""Supported HA manager reload and disable paths cancel the old runtime."""

import pytest
from homeassistant.config_entries import ConfigEntryDisabler
from pytest_homeassistant_custom_component.common import MockConfigEntry
from test_native import mapping

from custom_components.ecoflow_smart_charge.const import DOMAIN


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_options_flow_reloads_to_shadow_and_disable_cleans_resources(hass):
    entry = MockConfigEntry(domain=DOMAIN, data=mapping(hass))
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    original = entry.runtime_data
    flow = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        flow["flow_id"],
        user_input={"master": True, "mode": "shadow", "minimum_price_advantage_percent": 26.0},
    )
    assert result["type"] == "create_entry"
    await hass.async_block_till_done()
    assert original.closed and not original.cancels and not original.listeners
    assert entry.runtime_data is not original
    assert entry.runtime_data.mode == "shadow"
    assert entry.options["minimum_price_advantage_percent"] == 26.0
    runtime = entry.runtime_data
    await hass.config_entries.async_set_disabled_by(entry.entry_id, ConfigEntryDisabler.USER)
    await hass.async_block_till_done()
    assert runtime.closed and not runtime.cancels and not runtime.listeners
    assert entry.disabled_by is ConfigEntryDisabler.USER
