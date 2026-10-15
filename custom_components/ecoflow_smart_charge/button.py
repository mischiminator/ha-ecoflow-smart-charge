"""Non-writing recompute button."""
from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback

class RecalculateButton(ButtonEntity):
    _attr_has_entity_name = True
    _attr_name = "Recalculate shadow plan"
    def __init__(self, entry): self._entry = entry; self._attr_unique_id = f"{entry.entry_id}_recalculate"
    async def async_press(self):
        self._entry.runtime_data.status = "shadow_recalculated"

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback): async_add_entities([RecalculateButton(entry)])
