"""EcoFlow Smart Charge Home Assistant integration lifecycle."""
from __future__ import annotations

from typing import TYPE_CHECKING

from .const import DOMAIN, STORE_VERSION
from .runtime import Runtime
from .storage import PersistentSessionStore

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

PLATFORMS = ("sensor", "binary_sensor", "number", "select", "switch", "button")


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a safe, shadow-default per-entry runtime without issuing commands."""
    from homeassistant.helpers.storage import Store

    store = PersistentSessionStore(Store(hass, STORE_VERSION, f"{DOMAIN}.{entry.entry_id}"))
    await store.async_load()
    # Journal recovery is intentionally pending-only here: no restart-time service call
    # occurs before an operator confirms recovery and a later readback validates it.
    mode = entry.options.get("mode", "shadow")
    runtime = Runtime(mode, store, lambda entity: hass.states.get(entity).state, lambda entity, value: None)
    if store.record is not None:
        runtime.status = "recovery_pending"
    entry.runtime_data = runtime
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload platforms; a pending journal remains for explicit recovery after reload."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
