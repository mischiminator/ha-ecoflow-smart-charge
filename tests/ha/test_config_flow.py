"""Setup selects devices and provider entries; every entity is resolved, none typed in."""

from __future__ import annotations

import pytest
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import async_fire_time_changed
from test_native import selection

from custom_components.ecoflow_smart_charge.const import DOMAIN


async def submit(hass, user_input):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    assert result["type"] == "form"
    return await hass.config_entries.flow.async_configure(result["flow_id"], user_input)


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_config_flow_rejects_empty_battery_selection(hass) -> None:
    chosen = selection(hass)
    result = await submit(hass, {**chosen, "battery_devices": []})
    assert result["type"] == "form"
    assert result["errors"]["base"] == "battery_count_invalid"


@pytest.mark.usefixtures("enable_custom_integrations")
@pytest.mark.parametrize("count", [1, 2, 4])
async def test_config_flow_accepts_any_battery_count(hass, count) -> None:
    result = await submit(hass, selection(hass, batteries=count, pv=None))
    assert result["type"] == "create_entry"
    entry = result["result"]
    await hass.async_block_till_done()
    for key in ("soc_entities", "reserve_entities", "charge_energy_entities"):
        assert len(entry.data[key]) == count
    assert len(entry.runtime_data.writers) == count
    assert entry.data["capacities_kwh"] == [1.92] * count
    assert entry.runtime_data._mapping_valid()
    assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_config_flow_rejects_device_without_required_entity(hass) -> None:
    chosen = selection(hass)
    registry = er.async_get(hass)
    reserve = next(
        e
        for e in er.async_entries_for_device(registry, chosen["battery_devices"][0])
        if e.domain == "number"
    )
    registry.async_update_entity(reserve.entity_id, disabled_by=er.RegistryEntryDisabler.USER)
    result = await submit(hass, chosen)
    assert result["errors"]["base"] == "device_entities_missing"


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_form_prefills_single_candidates(hass) -> None:
    er.async_get(hass).async_get_or_create(
        "sensor",
        "integration",
        "pv_verbrauch",
        suggested_object_id="pv_riemann",
        original_device_class="energy",
    )
    chosen = selection(hass)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    suggested = {
        str(key): key.description["suggested_value"]
        for key in result["data_schema"].schema
        if key.description and "suggested_value" in key.description
    }
    assert set(suggested["battery_devices"]) == set(chosen["battery_devices"])
    for key in ("meter_device", "forecast_entry", "prices_entry", "pv_entity"):
        assert suggested[key] == chosen[key], key


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_without_pv_meter_the_entry_integrates_battery_pv_power(hass, freezer) -> None:
    freezer.move_to("2026-06-01T10:00:00+00:00")
    result = await submit(hass, selection(hass, pv=None))
    assert result["type"] == "create_entry"
    entry = result["result"]
    await hass.async_block_till_done()
    assert "pv_entity" not in entry.data
    pv = entry.runtime_data.reader.data["pv_entity"]
    assert pv is not None and hass.states.get(pv).state == "0.0"
    # 3 x 120 W held for 30 one-minute ticks = 0.18 kWh.
    for _ in range(30):
        freezer.tick(60)
        async_fire_time_changed(hass)
        await hass.async_block_till_done()
    for entity in entry.data["pv_power_entities"]:
        hass.states.async_set(entity, "0", {"unit_of_measurement": "W"})
    await hass.async_block_till_done()
    assert float(hass.states.get(pv).state) == pytest.approx(0.18)
    # A gap longer than the integration limit is skipped, not extrapolated.
    for entity in entry.data["pv_power_entities"]:
        hass.states.async_set(entity, "500", {"unit_of_measurement": "W"})
    freezer.tick(3600)
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert float(hass.states.get(pv).state) == pytest.approx(0.18)
    assert hass.states.get(pv).attributes["state_class"] == "total_increasing"
    assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_reload_follows_renamed_device_entities(hass) -> None:
    result = await submit(hass, selection(hass))
    entry = result["result"]
    await hass.async_block_till_done()
    old = entry.data["reserve_entities"][0]
    er.async_get(hass).async_update_entity(old, new_entity_id="number.renamed_reserve")
    hass.states.async_set("number.renamed_reserve", "11", {"unit_of_measurement": "%"})
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.data["reserve_entities"][0] == "number.renamed_reserve"
    assert entry.runtime_data.writers[0] == "number.renamed_reserve"
    assert await hass.config_entries.async_unload(entry.entry_id)


def test_model_capacity_table() -> None:
    from custom_components.ecoflow_smart_charge.sources import model_capacity

    assert model_capacity("Stream Ultra X") == 3.84
    for model in ("Stream Ultra", "Stream PRO", "Stream AC", "stream max"):
        assert model_capacity(model) == 1.92
    assert model_capacity("Smart Meter") is None
    assert model_capacity(None) is None


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_flow_stores_capacity_per_device_model(hass) -> None:
    chosen = selection(hass, models=["Stream Ultra X", "Stream AC", "Unknown 9000"])
    result = await submit(hass, chosen)
    assert result["result"].data["capacities_kwh"] == [3.84, 1.92, None]


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_missing_system_load_sensor_keeps_setup_working(hass) -> None:
    chosen = selection(hass)
    registry = er.async_get(hass)
    load = next(
        e
        for e in er.async_entries_for_device(registry, chosen["battery_devices"][1])
        if e.unique_id.endswith("-powGetSysLoad")
    )
    registry.async_remove(load.entity_id)
    result = await submit(hass, chosen)
    assert result["type"] == "create_entry"
    assert "sys_load_entities" not in result["result"].data
    assert await hass.config_entries.async_unload(result["result"].entry_id)
