"""Resolve selected devices and provider entries into the reader's entity mapping."""

from __future__ import annotations

from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN

ECOFLOW = "ecoflow_cloud"
FORECAST_SOLAR = "forecast_solar"
TIBBER_PRICES = "tibber_prices"
SUN = "sun.sun"
OWN_PV_KEY = "pv_energy"

# ecoflow_cloud unique IDs are "ecoflow-api-<serial>-<key>" for every Stream model.
BATTERY = {
    "soc_entities": ("sensor", "-f32ShowSoc"),
    "reserve_entities": ("number", "-backupReverseSoc"),
    "self_powered_entities": ("switch", "-energyStrategyOperateMode-operateSelfPoweredOpen"),
    "charge_energy_entities": ("sensor", "-accuChgEnergy"),
    "discharge_energy_entities": ("sensor", "-accuDsgEnergy"),
    "pv_power_entities": ("sensor", "-powGetPvSum"),
}
METER = ("sensor", "-gridConnectionDataRecord-totalActiveEnergy")
# Provider integrations use "<config entry id>_<key>" unique IDs.
FORECAST = {
    "forecast_today_entity": ("sensor", "energy_production_today"),
    "forecast_remaining_entity": ("sensor", "energy_production_today_remaining"),
    "forecast_tomorrow_entity": ("sensor", "energy_production_tomorrow"),
}
PRICES = {
    "price_entity": ("sensor", "current_interval_price"),
    "price_window_entity": ("binary_sensor", "best_price_period"),
}


# Usable capacity by ecoflow_cloud device model (datasheet values); first match wins.
MODEL_CAPACITY_KWH = (
    ("stream ultra x", 3.84),
    ("stream", 1.92),
)


def model_capacity(model):
    """Capacity for a known model, else None so the configured fallback applies."""
    name = (model or "").strip().lower()
    return next((kwh for prefix, kwh in MODEL_CAPACITY_KWH if name.startswith(prefix)), None)


class SourceMissing(ValueError):
    """A selected device or provider entry lacks a required, enabled entity."""


def _device_entities(registry, device_id, domain, suffix):
    return [
        e.entity_id
        for e in er.async_entries_for_device(registry, device_id)
        if e.platform == ECOFLOW and e.domain == domain and e.unique_id.endswith(suffix)
    ]


def _device_entity(registry, device_id, domain, suffix):
    found = _device_entities(registry, device_id, domain, suffix)
    if len(found) != 1:
        raise SourceMissing(suffix)
    return found[0]


def _entry_entity(registry, platform, entry_id, domain, key):
    entity = registry.async_get_entity_id(domain, platform, f"{entry_id}_{key}")
    if entity is None or registry.async_get(entity).disabled:
        raise SourceMissing(key)
    return entity


def resolve(hass, selection):
    """Return the reader mapping for one flow selection or raise SourceMissing."""
    registry = er.async_get(hass)
    devices = selection["battery_devices"]
    data = {
        key: [_device_entity(registry, device, *spec) for device in devices]
        for key, spec in BATTERY.items()
    }
    models = dr.async_get(hass)
    data["capacities_kwh"] = [
        model_capacity(getattr(models.async_get(device), "model", None)) for device in devices
    ]
    data["grid_energy_entity"] = _device_entity(registry, selection["meter_device"], *METER)
    for key, spec in FORECAST.items():
        data[key] = _entry_entity(registry, FORECAST_SOLAR, selection["forecast_entry"], *spec)
    for key, spec in PRICES.items():
        data[key] = _entry_entity(registry, TIBBER_PRICES, selection["prices_entry"], *spec)
    data["sun_entity"] = SUN
    return data


def own_pv_entity(hass, entry_id):
    return er.async_get(hass).async_get_entity_id("sensor", DOMAIN, f"{entry_id}_{OWN_PV_KEY}")


def ecoflow_devices(hass, domain, suffix):
    """Device IDs that expose exactly one matching ecoflow_cloud entity."""
    registry, devices = er.async_get(hass), dr.async_get(hass)
    return [
        device.id
        for entry in hass.config_entries.async_entries(ECOFLOW)
        for device in dr.async_entries_for_config_entry(devices, entry.entry_id)
        if len(_device_entities(registry, device.id, domain, suffix)) == 1
    ]


def provider_entries(hass, domain):
    return [e.entry_id for e in hass.config_entries.async_entries(domain)]


def pv_energy_candidates(hass):
    """Existing Riemann-sum PV energy sensors; the user keeps their history."""
    return [
        e.entity_id
        for e in er.async_get(hass).entities.values()
        if e.platform == "integration"
        and e.domain == "sensor"
        and not e.disabled
        and (e.device_class or e.original_device_class) == "energy"
        and "pv" in f"{e.entity_id} {e.name or ''} {e.original_name or ''}".lower()
    ]
