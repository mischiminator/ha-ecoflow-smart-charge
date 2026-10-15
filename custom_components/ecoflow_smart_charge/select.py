"""Options-backed controller mode selector."""
from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback


class ModeSelect(SelectEntity):
    _attr_has_entity_name = True
    _attr_name = "Controller mode"
    _attr_options = ("shadow", "armed", "active")
    def __init__(self, entry): self._entry = entry; self._attr_unique_id = f"{entry.entry_id}_mode"
    @property
    def current_option(self): return self._entry.runtime_data.mode
    async def async_select_option(self, option):
        if option == "active": raise ValueError("Use explicit cutover service after safety checks")
        self._entry.runtime_data.mode = option
        self.async_write_ha_state()

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback): async_add_entities([ModeSelect(entry)])
