"""Config and options flows with user-selected, validation-ready entities."""
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.helpers import selector

from .const import DEFAULT_CHARGE_CEILING_CT, DEFAULT_MINIMUM_PRICE_ADVANTAGE, DOMAIN

CONF_GRID_ENERGY = "grid_energy_entity"
CONF_PRICE = "price_entity"
CONF_PRICE_WINDOW = "price_window_entity"
CONF_PV = "pv_entity"
CONF_SOC = "soc_entities"
CONF_RESERVES = "reserve_entities"
CONF_SELF_POWERED = "self_powered_entities"
CONF_OPERATING_MODE = "operating_mode_entities"


def _entity_selector(domains: list[str], multiple: bool = False) -> selector.EntitySelector:
    return selector.EntitySelector(selector.EntitySelectorConfig(domain=domains, multiple=multiple))


class EcoFlowSmartChargeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            triples = (CONF_SOC, CONF_RESERVES, CONF_SELF_POWERED, CONF_OPERATING_MODE)
            if any(len(user_input.get(key, [])) != 3 for key in triples):
                errors["base"] = "three_batteries_required"
            elif len(set(user_input[CONF_RESERVES])) != 3:
                errors["base"] = "duplicate_reserves"
            else:
                await self.async_set_unique_id(f"{DOMAIN}:{user_input[CONF_GRID_ENERGY]}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)
        schema = vol.Schema({
            vol.Required(CONF_NAME, default="EcoFlow Smart Charge"): str,
            vol.Required(CONF_GRID_ENERGY): _entity_selector(["sensor"]),
            vol.Required(CONF_PRICE): _entity_selector(["sensor"]),
            vol.Required(CONF_PRICE_WINDOW): _entity_selector(["binary_sensor"]),
            vol.Required(CONF_PV): _entity_selector(["sensor"]),
            vol.Required(CONF_SOC): _entity_selector(["sensor"], True),
            vol.Required(CONF_RESERVES): _entity_selector(["number"], True),
            vol.Required(CONF_SELF_POWERED): _entity_selector(["switch"], True),
            vol.Required(CONF_OPERATING_MODE): _entity_selector(["select"], True),
        })
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    @config_entries.callback
    def async_get_options_flow(config_entry):
        return EcoFlowSmartChargeOptionsFlow()


class EcoFlowSmartChargeOptionsFlow(config_entries.OptionsFlow):
    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        schema = vol.Schema({
            vol.Required("mode", default=self.config_entry.options.get("mode", "shadow")): selector.SelectSelector(
                selector.SelectSelectorConfig(options=["shadow", "armed", "active"])
            ),
            vol.Required("minimum_price_advantage_percent", default=self.config_entry.options.get("minimum_price_advantage_percent", DEFAULT_MINIMUM_PRICE_ADVANTAGE)): vol.All(vol.Coerce(float), vol.Range(min=0, max=100)),
            vol.Required("charge_ceiling_ct", default=self.config_entry.options.get("charge_ceiling_ct", DEFAULT_CHARGE_CEILING_CT)): vol.Coerce(float),
        })
        return self.async_show_form(step_id="init", data_schema=schema)
