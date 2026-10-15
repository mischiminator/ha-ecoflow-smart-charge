"""A reversible armed indicator; never a hardware switch."""
from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback


class ArmedSwitch(SwitchEntity):
    _attr_has_entity_name = True
    _attr_name = "Armed"
    def __init__(self, entry): self._entry = entry; self._attr_unique_id = f"{entry.entry_id}_armed"
    @property
    def is_on(self): return self._entry.runtime_data.mode == "armed"
    async def async_turn_on(self, **kwargs): self._entry.runtime_data.mode = "armed"; self.async_write_ha_state()
    async def async_turn_off(self, **kwargs): self._entry.runtime_data.mode = "shadow"; self.async_write_ha_state()

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback): async_add_entities([ArmedSwitch(entry)])
