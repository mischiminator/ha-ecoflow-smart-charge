"""Recalculation uses the same runtime gatekeeper as timers and services."""

from homeassistant.components.button import ButtonEntity

from .entity import RuntimeEntity


class RecalculateButton(RuntimeEntity, ButtonEntity):
    async def async_press(self):
        await self.runtime.async_recalculate()


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([RecalculateButton(entry, "recalculate", "Recalculate")])
