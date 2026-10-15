"""Mode display with stop-only selection; active requires explicit cutover."""

from typing import ClassVar

from homeassistant.components.select import SelectEntity

from .entity import RuntimeEntity


class ModeSelect(RuntimeEntity, SelectEntity):
    _attr_options: ClassVar[list[str]] = ["shadow", "active"]

    @property
    def current_option(self):
        return "active" if self.runtime.mode == "active" else "shadow"

    async def async_select_option(self, option):
        if option != "shadow":
            raise ValueError("explicit cutover service required")
        await self.runtime.async_set_shadow()


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([ModeSelect(entry, "mode", "Controller mode")])
