"""Status sensors."""
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback


class StatusSensor(SensorEntity):
    _attr_has_entity_name = True
    _attr_name = "Controller status"
    _attr_icon = "mdi:battery-sync"
    def __init__(self, entry): self._entry = entry; self._attr_unique_id = f"{entry.entry_id}_status"
    @property
    def native_value(self): return self._entry.runtime_data.status

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    async_add_entities([StatusSensor(entry)])
