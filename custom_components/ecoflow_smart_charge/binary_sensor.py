"""Safety binary entities."""
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback

class ShadowActive(BinarySensorEntity):
    _attr_has_entity_name = True
    _attr_name = "Shadow active"
    def __init__(self, entry): self._entry = entry; self._attr_unique_id = f"{entry.entry_id}_shadow_active"
    @property
    def is_on(self): return self._entry.runtime_data.mode == "shadow"

class RecoveryPending(BinarySensorEntity):
    _attr_has_entity_name = True
    _attr_name = "Recovery pending"
    def __init__(self, entry): self._entry = entry; self._attr_unique_id = f"{entry.entry_id}_recovery_pending"
    @property
    def is_on(self): return self._entry.runtime_data.status == "recovery_pending"

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    async_add_entities([ShadowActive(entry), RecoveryPending(entry)])
