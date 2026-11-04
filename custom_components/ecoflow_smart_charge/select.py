"""Controller mode: shadow plans only, active controls the reserves."""

from typing import ClassVar

from homeassistant.components.select import SelectEntity

from .config_flow import MODES
from .entity import RuntimeEntity


class ModeSelect(RuntimeEntity, SelectEntity):
    _attr_options: ClassVar[list[str]] = list(MODES)

    @property
    def current_option(self):
        return self.runtime.mode

    async def async_select_option(self, option):
        await self.runtime.async_set_setting("mode", option)
        if option == "active":
            await self.runtime.async_recalculate()


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([ModeSelect(entry, "mode")])
