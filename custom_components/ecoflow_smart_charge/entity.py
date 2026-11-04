"""Entry-local push entities; no entity writes devices directly."""

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity import Entity

from .const import DOMAIN


class RuntimeEntity(Entity):
    _attr_should_poll = False
    _attr_has_entity_name = True

    def __init__(self, entry, key):
        self.entry = entry
        self.runtime = entry.runtime_data
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_translation_key = key
        # One service device per entry lets the dashboard card find its entities.
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            entry_type=DeviceEntryType.SERVICE,
        )
        self.key = key

    async def async_added_to_hass(self):
        self.async_on_remove(self.runtime.subscribe(self.async_write_ha_state))
