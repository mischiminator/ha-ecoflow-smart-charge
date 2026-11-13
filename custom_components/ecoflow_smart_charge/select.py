"""Controller mode: shadow plans only, active controls the reserves."""

from typing import ClassVar

from homeassistant.components.select import SelectEntity

from .config_flow import MODES
from .entity import RuntimeEntity
from .settings import CHARGING_POLICIES, SETTINGS_MODES, effective_settings


class ModeSelect(RuntimeEntity, SelectEntity):
    _attr_options: ClassVar[list[str]] = list(MODES)

    @property
    def current_option(self):
        return self.runtime.mode

    async def async_select_option(self, option):
        await self.runtime.async_set_setting("mode", option)
        if option == "active":
            await self.runtime.async_recalculate()


class SettingsSelect(RuntimeEntity, SelectEntity):
    def __init__(self, entry, key, choices):
        super().__init__(entry, key)
        self._attr_options = list(choices)

    @property
    def current_option(self):
        return effective_settings(self.entry.options)[self.key]

    async def async_select_option(self, option):
        await self.runtime.async_set_setting(self.key, option)


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities(
        [
            ModeSelect(entry, "mode"),
            SettingsSelect(entry, "settings_mode", SETTINGS_MODES),
            SettingsSelect(entry, "charging_policy", CHARGING_POLICIES),
        ]
    )
