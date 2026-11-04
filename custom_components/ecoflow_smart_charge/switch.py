"""Persistent master permission, initially off; no hardware bypass."""

from homeassistant.components.switch import SwitchEntity

from .entity import RuntimeEntity


class MasterSwitch(RuntimeEntity, SwitchEntity):
    @property
    def is_on(self):
        return self.entry.options.get("master", False)

    async def async_turn_on(self, **kwargs):
        await self.runtime.async_set_setting("master", True)

    async def async_turn_off(self, **kwargs):
        await self.runtime.async_set_setting("master", False)


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([MasterSwitch(entry, "master")])
