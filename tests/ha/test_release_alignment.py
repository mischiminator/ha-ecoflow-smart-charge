"""Final native entity inventory must have complete, connected localizations."""

import json
from pathlib import Path

import pytest
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry
from test_native import mapping

from custom_components.ecoflow_smart_charge.const import DOMAIN


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_all_native_entities_connect_complete_translation_inventory(hass):
    entry = MockConfigEntry(domain=DOMAIN, data=mapping(hass))
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    component = Path(__file__).resolve().parents[2] / "custom_components" / DOMAIN
    locales = [
        json.loads((component / file).read_text())["entity"]
        for file in ("strings.json", "translations/en.json", "translations/de.json")
    ]
    entities = er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)
    assert {entity.domain for entity in entities} == {
        "sensor",
        "binary_sensor",
        "number",
        "switch",
        "select",
        "button",
    }
    for entity in entities:
        key = entity.unique_id.removeprefix(entry.entry_id + "_")
        for locale in locales:
            assert key in locale[entity.domain], (entity.domain, key)
            assert locale[entity.domain][key]["name"]
        assert entity.translation_key == key, (entity.domain, key)
        assert hass.states.get(entity.entity_id) is not None
    assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.usefixtures("enable_custom_integrations")
@pytest.mark.parametrize("phase", ["shadow", "active", "pending", "blocked", "unloaded"])
async def test_diagnostics_never_disclose_entry_or_nested_canaries(hass, phase):
    from custom_components.ecoflow_smart_charge.diagnostics import (
        async_get_config_entry_diagnostics,
    )

    canary = "PRIVATE-DIAGNOSTIC-CANARY"
    data = {**mapping(hass), "private_nested": [{"token": canary}]}
    entry = MockConfigEntry(
        domain=DOMAIN, data=data, options={"private_option": canary}, entry_id=canary
    )
    entry.add_to_hass(hass)
    if phase != "unloaded":
        assert await hass.config_entries.async_setup(entry.entry_id)
        runtime = entry.runtime_data
        if phase == "active":
            runtime.mode = "active"
        if phase == "pending":
            await runtime.journal.async_capture_before_command(
                canary, {e: 11.0 for e in data["reserve_entities"]}, {}
            )
        if phase == "blocked":
            runtime.journal.blocked = True
        runtime.last_error = canary
    result = await async_get_config_entry_diagnostics(hass, entry)
    assert canary not in json.dumps(result)
    assert result["recovery_pending"] == (phase in ("pending", "blocked"))
    assert set(result) == {
        "mode",
        "status",
        "recovery_pending",
        "session_phase",
        "configured_source_count",
        "domain",
    }
    if phase not in ("pending", "blocked", "unloaded"):
        assert await hass.config_entries.async_unload(entry.entry_id)
