"""Validated native source selectors and bounded options."""

from __future__ import annotations

import math

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import DOMAIN
from .planner.core import MAX_BATTERIES
from .settings import (
    CHARGING_POLICIES,
    NEW_ENTRY_OPTIONS,
    SETTINGS,
    SETTINGS_MODES,
    effective_settings,
    merge_settings,
)

SINGLES = (
    "grid_energy_entity",
    "price_entity",
    "price_window_entity",
    "forecast_today_entity",
    "forecast_remaining_entity",
    "forecast_tomorrow_entity",
    "sun_entity",
)
# One entity per battery each.
TRIPLES = (
    "soc_entities",
    "reserve_entities",
    "self_powered_entities",
    "charge_energy_entities",
    "discharge_energy_entities",
)
# What the user picks; everything in SINGLES/TRIPLES is resolved from it.
FIELDS = (
    "name",
    "battery_devices",
    "meter_device",
    "forecast_entry",
    "prices_entry",
    "pv_entity",
    "tariff_key",
)
MODES = ("shadow", "active")


def validate_settings(values):
    for key, (_, lo, hi) in SETTINGS.items():
        if key in values:
            value = values[key]
            if (
                isinstance(value, bool)
                or not isinstance(value, (float, int))
                or not math.isfinite(value)
                or not lo <= value <= hi
            ):
                raise ValueError("invalid_setting")
    if "master" in values and not isinstance(values["master"], bool):
        raise ValueError("invalid_master")
    if values.get("mode", "shadow") not in MODES:
        raise ValueError("invalid_mode")
    for key, choices in (("settings_mode", SETTINGS_MODES), ("charging_policy", CHARGING_POLICIES)):
        if key in values and (not isinstance(values[key], str) or values[key] not in choices):
            raise ValueError("invalid_setting")
    if set(values) - set(SETTINGS) - {"master", "mode", "settings_mode", "charging_policy"}:
        raise ValueError("unknown_setting")
    return dict(values)


def validate_mapping(hass, data):
    """States and units of a mapping resolve() built; counts and domains are already right."""
    try:
        if not data["tariff_key"].strip():
            return "source_invalid"
        # Without a selected PV meter the integration integrates PV power itself.
        pv = [data["pv_entity"]] if data.get("pv_entity") else []
        selected = [data[k] for k in SINGLES] + [e for k in TRIPLES for e in data[k]] + pv
        energy = [
            data["grid_energy_entity"],
            *pv,
            *data["charge_energy_entities"],
            *data["discharge_energy_entities"],
        ]
        if len(set(energy)) != len(energy):
            return "source_invalid"
        for entity in selected:
            state = hass.states.get(entity)
            if state is None or state.state in ("unknown", "unavailable"):
                return "source_invalid"
        for entity in energy + [
            data[k]
            for k in (
                "forecast_today_entity",
                "forecast_remaining_entity",
                "forecast_tomorrow_entity",
            )
        ]:
            if hass.states.get(entity).attributes.get("unit_of_measurement") not in ("Wh", "kWh"):
                return "unit_invalid"
        for entity in data["soc_entities"] + data["reserve_entities"]:
            state = hass.states.get(entity)
            if (
                state.attributes.get("unit_of_measurement") != "%"
                or not 0 <= float(state.state) <= 100
            ):
                return "unit_invalid"
        if hass.states.get(data["price_entity"]).attributes.get("unit_of_measurement") not in (
            "EUR/kWh",
            "ct/kWh",
        ):
            return "unit_invalid"
    except KeyError, TypeError, ValueError, AttributeError:
        return "source_invalid"
    return None


def resolve_selection(hass, user_input):
    """Selection plus resolved entity mapping, or a form error."""
    from .sources import SourceMissing, resolve

    selection = {k: user_input[k] for k in FIELDS if user_input.get(k)}
    devices = selection.get("battery_devices", [])
    if not 1 <= len(set(devices)) == len(devices) <= MAX_BATTERIES:
        return None, "battery_count_invalid"
    try:
        data = {**selection, **resolve(hass, selection)}
    except KeyError, SourceMissing:
        return None, "device_entities_missing"
    return data, validate_mapping(hass, data)


async def tibber_homes(hass):
    try:
        response = await hass.services.async_call(
            "tibber", "get_prices", {}, blocking=True, return_response=True
        )
        return sorted(response["prices"])
    except Exception:  # noqa: BLE001 - only a suggestion source, the field stays editable
        return []


def _only(values):
    return values[0] if len(values) == 1 else None


async def suggestions(hass):
    from .sources import (
        BATTERY,
        FORECAST_SOLAR,
        METER,
        TIBBER_PRICES,
        ecoflow_devices,
        provider_entries,
        pv_energy_candidates,
    )

    homes = await tibber_homes(hass)
    batteries = ecoflow_devices(hass, *BATTERY["reserve_entities"])
    values = {
        "battery_devices": batteries if len(batteries) <= MAX_BATTERIES else None,
        "meter_device": _only(ecoflow_devices(hass, *METER)),
        "forecast_entry": _only(provider_entries(hass, FORECAST_SOLAR)),
        "prices_entry": _only(provider_entries(hass, TIBBER_PRICES)),
        "pv_entity": _only(pv_energy_candidates(hass)),
        "tariff_key": _only(homes),
    }
    return homes, {k: v for k, v in values.items() if v}


def mapping_schema(homes=()):
    from .sources import ECOFLOW, FORECAST_SOLAR, TIBBER_PRICES

    def device(multiple=False):
        return selector.DeviceSelector(
            selector.DeviceSelectorConfig(integration=ECOFLOW, multiple=multiple)
        )

    def entry(integration):
        return selector.ConfigEntrySelector(
            selector.ConfigEntrySelectorConfig(integration=integration)
        )

    return vol.Schema(
        {
            vol.Required("name", default="EcoFlow Smart Charge"): str,
            vol.Required("battery_devices"): device(multiple=True),
            vol.Required("meter_device"): device(),
            vol.Required("forecast_entry"): entry(FORECAST_SOLAR),
            vol.Required("prices_entry"): entry(TIBBER_PRICES),
            vol.Optional("pv_entity"): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", device_class="energy")
            ),
            vol.Required("tariff_key"): selector.SelectSelector(
                selector.SelectSelectorConfig(options=list(homes), custom_value=True)
            ),
        }
    )


class EcoFlowSmartChargeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            data, error = resolve_selection(self.hass, user_input)
            if error:
                errors["base"] = error
            else:
                # Physical reserve targets, not private source IDs, determine duplicate ownership.
                chosen = set(data["reserve_entities"])
                if any(
                    chosen.intersection(e.data.get("reserve_entities", []))
                    for e in self._async_current_entries()
                ):
                    return self.async_abort(reason="already_configured")
                return self.async_create_entry(
                    title=data["name"], data=data, options=NEW_ENTRY_OPTIONS
                )
        homes, suggested = await suggestions(self.hass)
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                mapping_schema(homes), user_input or suggested
            ),
            errors=errors,
        )

    async def async_step_reconfigure(self, user_input=None):
        entry = self._get_reconfigure_entry()
        journal = getattr(getattr(entry, "runtime_data", None), "journal", None)
        if journal is None:
            from homeassistant.helpers.storage import Store

            from .const import STORE_VERSION
            from .storage import PersistentSessionStore

            journal = PersistentSessionStore(
                Store(self.hass, STORE_VERSION, f"{DOMAIN}.{entry.entry_id}")
            )
            await journal.async_load()
        if journal.blocked or journal.record:
            return self.async_abort(reason="recovery_pending")
        errors = {}
        if user_input is not None:
            data, error = resolve_selection(self.hass, user_input)
            if error:
                errors["base"] = error
            else:
                chosen = set(data["reserve_entities"])
                if any(
                    e.entry_id != entry.entry_id
                    and chosen.intersection(e.data.get("reserve_entities", []))
                    for e in self._async_current_entries()
                ):
                    return self.async_abort(reason="already_configured")
                # Replace, not merge: an emptied PV field switches to the own PV sensor.
                return self.async_update_reload_and_abort(entry, data=data)
        homes, _ = await suggestions(self.hass)
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(
                mapping_schema(homes), user_input or entry.data
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return EcoFlowSmartChargeOptionsFlow()


class EcoFlowSmartChargeOptionsFlow(config_entries.OptionsFlow):
    async def async_step_init(self, user_input=None):
        errors = {}
        if user_input is not None:
            try:
                validate_settings(user_input)
                if set(user_input) != {"settings_mode"}:
                    raise ValueError("invalid_setting")
                self._settings_mode = user_input["settings_mode"]
                return await self.async_step_settings()
            except ValueError as err:
                errors["base"] = str(err)
        current = effective_settings(self.config_entry.options)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        "settings_mode", default=current["settings_mode"]
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=list(SETTINGS_MODES), translation_key="settings_mode"
                        )
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_settings(self, user_input=None):
        errors = {}
        simple = self._settings_mode == "simple"
        allowed = set() if simple else set(SETTINGS)
        allowed |= {"master", "mode"}
        if simple:
            allowed.add("charging_policy")
        if user_input is not None:
            try:
                if set(user_input) - allowed:
                    raise ValueError("unknown_setting")
                options = merge_settings(
                    self.config_entry.options,
                    {
                        **user_input,
                        "settings_mode": self._settings_mode,
                    },
                )
                return self.async_create_entry(title="", data=options)
            except ValueError as err:
                errors["base"] = str(err)
        current = {**{key: spec[0] for key, spec in SETTINGS.items()}, **self.config_entry.options}
        schema = {
            vol.Optional("master", default=current.get("master", False)): bool,
            vol.Optional("mode", default=current.get("mode", "shadow")): vol.In(MODES),
        }
        if simple:
            schema[
                vol.Optional("charging_policy", default=current.get("charging_policy", "balanced"))
            ] = selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=list(CHARGING_POLICIES), translation_key="charging_policy"
                )
            )
        for key, (_, lo, hi) in SETTINGS.items():
            if key in allowed:
                schema[vol.Optional(key, default=current[key])] = vol.All(
                    vol.Coerce(float), vol.Range(min=lo, max=hi)
                )
        return self.async_show_form(
            step_id="settings", data_schema=vol.Schema(schema), errors=errors
        )
