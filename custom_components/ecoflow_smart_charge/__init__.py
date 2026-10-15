"""EcoFlow Smart Charge Home Assistant integration lifecycle."""
from __future__ import annotations

from typing import TYPE_CHECKING

import voluptuous as vol

from .const import DOMAIN, STORE_VERSION
from .runtime import Runtime
from .storage import PersistentSessionStore

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

PLATFORMS = ("sensor", "binary_sensor", "number", "select", "switch", "button")

SERVICE_RECALCULATE = "recalculate"
SERVICE_REQUEST_CUTOVER = "request_cutover"
SERVICE_CONFIRM_RECOVERY = "confirm_recovery"
SERVICE_SCHEMA = vol.Schema({vol.Required("config_entry_id"): str})


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Register explicit, entry-targeted services once for this domain."""
    async def _runtime(call):
        entry = hass.config_entries.async_get_entry(call.data["config_entry_id"])
        if entry is None or entry.domain != DOMAIN or entry.runtime_data is None:
            raise ValueError("configured controller entry is unavailable")
        return entry.runtime_data

    async def _recalculate(call):
        runtime = await _runtime(call)
        await runtime.async_recalculate()

    async def _request_cutover(call):
        runtime = await _runtime(call)
        await runtime.async_request_cutover()

    async def _confirm_recovery(call):
        runtime = await _runtime(call)
        await runtime.async_restore()

    for service, handler in (
        (SERVICE_RECALCULATE, _recalculate),
        (SERVICE_REQUEST_CUTOVER, _request_cutover),
        (SERVICE_CONFIRM_RECOVERY, _confirm_recovery),
    ):
        if not hass.services.has_service(DOMAIN, service):
            hass.services.async_register(DOMAIN, service, handler, schema=SERVICE_SCHEMA)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a safe, shadow-default per-entry runtime without issuing commands."""
    from homeassistant.helpers.storage import Store

    store = PersistentSessionStore(Store(hass, STORE_VERSION, f"{DOMAIN}.{entry.entry_id}"))
    await store.async_load()
    # Journal recovery is intentionally pending-only here: no restart-time service call
    # occurs before an operator confirms recovery and a later readback validates it.
    mode = entry.options.get("mode", "shadow")
    async def _read_reserve(entity: str) -> str | None:
        state = hass.states.get(entity)
        return state.state if state else None

    async def _write_reserve(entity: str, value: float) -> None:
        await hass.services.async_call(
            "number", "set_value", {"entity_id": entity, "value": value}, blocking=True
        )

    runtime = Runtime(mode, store, _read_reserve, _write_reserve)
    if store.record is not None:
        runtime.status = "recovery_pending"
    entry.runtime_data = runtime
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload platforms; a pending journal remains for explicit recovery after reload."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
