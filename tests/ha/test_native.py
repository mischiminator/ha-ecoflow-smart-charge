"""Real HA flow, entities, lifecycle and services; no device/network access."""

import pytest
import voluptuous as vol
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ecoflow_smart_charge.const import DOMAIN


def test_native_integration_declares_config_entry_only_schema():
    from custom_components.ecoflow_smart_charge import CONFIG_SCHEMA

    assert callable(CONFIG_SCHEMA)


def mapping(hass):
    data = {
        "name": "Synthetic controller",
        "grid_energy_entity": "sensor.grid",
        "pv_entity": "sensor.pv",
        "price_entity": "sensor.price",
        "price_window_entity": "binary_sensor.window",
        "forecast_today_entity": "sensor.forecast_today",
        "forecast_remaining_entity": "sensor.forecast_remaining",
        "forecast_tomorrow_entity": "sensor.forecast_tomorrow",
        "sun_entity": "sun.test",
        "tariff_key": "Synthetic",
    }
    specs = {
        "soc_entities": ("sensor", "soc", "50", "%"),
        "reserve_entities": ("number", "reserve", "11", "%"),
        "self_powered_entities": ("switch", "self", "on", None),
        "charge_energy_entities": ("sensor", "charge", "1", "kWh"),
        "discharge_energy_entities": ("sensor", "discharge", "1", "kWh"),
    }
    for key, (domain, name, value, unit) in specs.items():
        data[key] = [f"{domain}.{name}_{i}" for i in range(3)]
        for e in data[key]:
            hass.states.async_set(e, value, {"unit_of_measurement": unit} if unit else {})
    for key in (
        "grid_energy_entity",
        "pv_entity",
        "forecast_today_entity",
        "forecast_remaining_entity",
        "forecast_tomorrow_entity",
    ):
        hass.states.async_set(data[key], "1", {"unit_of_measurement": "kWh"})
    hass.states.async_set("sensor.price", "0.1", {"unit_of_measurement": "EUR/kWh"})
    hass.states.async_set("binary_sensor.window", "on")
    hass.states.async_set(
        "sun.test", "above_horizon", {"next_setting": "2026-10-15T20:00:00+00:00"}
    )
    return data


def selection(hass, *, pv="sensor.pv_riemann", prefix="BAT", batteries=3, models=None):
    """Registry-backed EcoFlow, Forecast.Solar and Tibber Prices sources as the flow sees them."""
    from homeassistant.helpers import device_registry as dr

    from custom_components.ecoflow_smart_charge.sources import BATTERY, FORECAST, METER, PRICES

    devices, entities = dr.async_get(hass), er.async_get(hass)
    providers = {}
    for domain in ("ecoflow_cloud", "forecast_solar", "tibber_prices"):
        providers[domain] = MockConfigEntry(domain=domain)
        providers[domain].add_to_hass(hass)
    eco = providers["ecoflow_cloud"]
    states = {
        "soc_entities": ("50", "%"),
        "reserve_entities": ("11", "%"),
        "self_powered_entities": ("on", None),
        "charge_energy_entities": ("1", "kWh"),
        "discharge_energy_entities": ("1", "kWh"),
        "pv_power_entities": ("120", "W"),
        "sys_load_entities": ("0", "W"),
    }

    def device(serial, specs, model=None):
        device_id = devices.async_get_or_create(
            config_entry_id=eco.entry_id, identifiers={("ecoflow_cloud", serial)}, model=model
        ).id
        for domain, suffix, value, unit in specs:
            entity = entities.async_get_or_create(
                domain,
                "ecoflow_cloud",
                f"ecoflow-api-{serial}{suffix}",
                device_id=device_id,
                config_entry=eco,
            ).entity_id
            hass.states.async_set(entity, value, {"unit_of_measurement": unit} if unit else {})
        return device_id

    models = models or ["Stream Ultra"] * batteries
    batteries = [
        device(f"{prefix}{i}", [(*BATTERY[key], *states[key]) for key in BATTERY], models[i])
        for i in range(batteries)
    ]
    meter = device(f"{prefix}METER", [(*METER, "1", "kWh")])
    for platform, keys, value, unit in (
        ("forecast_solar", FORECAST, "1", "kWh"),
        ("tibber_prices", PRICES, None, None),
    ):
        provider = providers[platform]
        for key, (domain, suffix) in keys.items():
            entity = entities.async_get_or_create(
                domain, platform, f"{provider.entry_id}_{suffix}", config_entry=provider
            ).entity_id
            if key == "price_entity":
                hass.states.async_set(entity, "21.5", {"unit_of_measurement": "ct/kWh"})
            elif key == "price_window_entity":
                hass.states.async_set(entity, "on")
            else:
                hass.states.async_set(entity, value, {"unit_of_measurement": unit})
    hass.states.async_set("sun.sun", "above_horizon", {"next_setting": "2026-10-15T20:00:00+00:00"})
    result = {
        "name": "Synthetic controller",
        "battery_devices": batteries,
        "meter_device": meter,
        "forecast_entry": providers["forecast_solar"].entry_id,
        "prices_entry": providers["tibber_prices"].entry_id,
        "tariff_key": "Synthetic",
    }
    if pv:
        hass.states.async_set(pv, "941.9", {"unit_of_measurement": "kWh"})
        result["pv_entity"] = pv
    return result


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_valid_flow_starts_in_shadow_and_options_select_mode(hass):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}, data=selection(hass)
    )
    assert result["type"] == "create_entry"
    entry = result["result"]
    assert entry.data["pv_entity"] == "sensor.pv_riemann"
    assert entry.data["sun_entity"] == "sun.sun"
    assert len(set(entry.data["reserve_entities"])) == 3
    await hass.async_block_till_done()
    assert entry.runtime_data.mode == "shadow"
    options = await hass.config_entries.options.async_init(entry.entry_id)
    from homeassistant.data_entry_flow import InvalidData

    with pytest.raises(InvalidData):
        await hass.config_entries.options.async_configure(
            options["flow_id"], user_input={"mode": "armed"}
        )
    options = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        options["flow_id"], user_input={"mode": "active"}
    )
    assert result["type"] == "create_entry"
    await hass.async_block_till_done()
    assert entry.options["mode"] == "active"
    assert entry.runtime_data.mode == "active"
    assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_real_entities_master_numbers_and_cleanup(hass):
    entry = MockConfigEntry(domain=DOMAIN, data=mapping(hass))
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    runtime = entry.runtime_data
    assert runtime.mode == "shadow"
    registry = er.async_get(hass)
    entities = {
        e.unique_id: e.entity_id
        for e in er.async_entries_for_config_entry(registry, entry.entry_id)
    }
    for key in (
        "master",
        "minimum_price_advantage",
        "mode",
        "recalculate",
        "permission",
        "status",
        "session_active",
        "solar_day",
        "plan_updated",
        "profile_samples",
        "corrected_forecast_kwh",
    ):
        assert entry.entry_id + "_" + key in entities
    master = entities[entry.entry_id + "_master"]
    await hass.services.async_call("switch", "turn_on", {"entity_id": master}, blocking=True)
    assert hass.states.get(master).state == "on"
    number = entities[entry.entry_id + "_minimum_price_advantage"]
    await hass.services.async_call(
        "number", "set_value", {"entity_id": number, "value": 27}, blocking=True
    )
    assert float(hass.states.get(number).state) == 27
    assert runtime.mode == "shadow"
    mode = entities[entry.entry_id + "_mode"]
    await hass.services.async_call(
        "select", "select_option", {"entity_id": mode, "option": "active"}, blocking=True
    )
    assert hass.states.get(mode).state == "active"
    assert runtime.mode == "active" and entry.options["mode"] == "active"
    assert entry.runtime_data is runtime
    assert len(runtime.cancels) >= 3
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert runtime.closed and not runtime.cancels
    assert not runtime.listeners


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_entry_service_requires_correct_target(hass):
    entry = MockConfigEntry(domain=DOMAIN, data=mapping(hass))
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    assert set(hass.services.async_services_for_domain(DOMAIN)) == {"recalculate"}
    with pytest.raises((vol.Invalid, ServiceValidationError)):
        await hass.services.async_call(DOMAIN, "recalculate", {}, blocking=True)
    with pytest.raises((vol.Invalid, ServiceValidationError)):
        await hass.services.async_call(
            DOMAIN, "recalculate", {"config_entry_id": "missing"}, blocking=True
        )
    assert entry.runtime_data.mode == "shadow"
    assert await hass.config_entries.async_unload(entry.entry_id)
