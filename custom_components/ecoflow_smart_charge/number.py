"""Bounded settings only; never physical reserve controls."""

from homeassistant.components.number import NumberEntity, NumberMode

from .config_flow import SETTINGS
from .entity import RuntimeEntity


class SettingNumber(RuntimeEntity, NumberEntity):
    _attr_mode = NumberMode.BOX

    def __init__(self, entry, key):
        super().__init__(
            entry, "minimum_price_advantage" if key == "minimum_price_advantage_percent" else key
        )
        self.setting = key
        self.default, self._attr_native_min_value, self._attr_native_max_value = SETTINGS[key]
        self._attr_native_step = 0.01 if key in ("efficiency", "capacity_kwh") else 0.1
        if key == "minimum_price_advantage_percent":
            self._attr_native_unit_of_measurement = "%"

    @property
    def native_value(self):
        return self.entry.options.get(self.setting, self.default)

    async def async_set_native_value(self, value):
        await self.runtime.async_set_setting(self.setting, value)


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([SettingNumber(entry, key) for key in SETTINGS])
