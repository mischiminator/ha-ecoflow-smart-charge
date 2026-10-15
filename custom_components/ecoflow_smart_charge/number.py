"""Safety setting number entity."""
from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback


class AdvantageNumber(NumberEntity):
    _attr_has_entity_name = True
    _attr_name = "Minimum price advantage"
    _attr_native_min_value = 0
    _attr_native_max_value = 100
    _attr_native_step = 1
    _attr_mode = NumberMode.BOX
    _attr_native_unit_of_measurement = "%"
    def __init__(self, entry): self._entry = entry; self._attr_unique_id = f"{entry.entry_id}_minimum_price_advantage"
    @property
    def native_value(self): return self._entry.options.get("minimum_price_advantage_percent", 20)
    async def async_set_native_value(self, value):
        self._entry.async_update(options={**self._entry.options, "minimum_price_advantage_percent": value})
        self.async_write_ha_state()

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback): async_add_entities([AdvantageNumber(entry)])
