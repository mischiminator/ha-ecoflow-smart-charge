"""Integration lifecycle and the explicitly targeted recalculate service."""

from __future__ import annotations

from typing import TYPE_CHECKING

import voluptuous as vol
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN, PLATFORMS, STORE_VERSION

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    from homeassistant.exceptions import ServiceValidationError

    async def handle(call):
        entry = hass.config_entries.async_get_entry(call.data["config_entry_id"])
        if entry is None or entry.domain != DOMAIN or getattr(entry, "runtime_data", None) is None:
            raise ServiceValidationError("configured controller entry is unavailable")
        try:
            await entry.runtime_data.async_recalculate()
        except (ValueError, OSError, RuntimeError) as err:
            raise ServiceValidationError(
                "controller request rejected: " + type(err).__name__
            ) from err

    await _register_card(hass)
    if not hass.services.has_service(DOMAIN, "recalculate"):
        hass.services.async_register(
            DOMAIN,
            "recalculate",
            handle,
            schema=vol.Schema({vol.Required("config_entry_id"): str}),
        )
    return True


async def _register_card(hass: HomeAssistant) -> None:
    """Serve the bundled dashboard card and load it on every frontend page."""
    if hass.http is None or "frontend" not in hass.config.components:
        return
    import hashlib
    from pathlib import Path

    from homeassistant.components.frontend import add_extra_js_url
    from homeassistant.components.http import StaticPathConfig

    from .const import CARD_URL

    path = Path(__file__).parent / "frontend" / "ecoflow-smart-charge-card.js"
    content = await hass.async_add_executor_job(path.read_bytes)
    await hass.http.async_register_static_paths([StaticPathConfig(CARD_URL, str(path), False)])
    # The content hash busts browser caches after every update.
    add_extra_js_url(hass, f"{CARD_URL}?v={hashlib.sha256(content).hexdigest()[:12]}")


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    from homeassistant.const import EVENT_HOMEASSISTANT_STARTED, EVENT_HOMEASSISTANT_STOP
    from homeassistant.core import callback
    from homeassistant.helpers.event import async_track_state_change_event, async_track_time_change
    from homeassistant.helpers.storage import Store

    from .reader import SourceReader
    from .runtime import Runtime
    from .storage import PersistentSessionStore

    journal = PersistentSessionStore(Store(hass, STORE_VERSION, f"{DOMAIN}.{entry.entry_id}"))
    await journal.async_load()
    if "battery_devices" in entry.data and journal.record is None and not journal.blocked:
        # Follow entity renames; a pending session keeps the mapping it saved reserves for.
        from .sources import SourceMissing, resolve

        try:
            resolved = resolve(hass, entry.data)
        except KeyError, SourceMissing:
            resolved = {}
        if resolved and any(entry.data.get(k) != v for k, v in resolved.items()):
            hass.config_entries.async_update_entry(entry, data={**entry.data, **resolved})
    reader = SourceReader(hass, entry, journal)

    async def read(entity):
        state = hass.states.get(entity)
        return (state.state, state.last_reported) if state else (None, None)

    def leader():
        from homeassistant.util import dt as dt_util

        from .reader import leader_reserve

        return leader_reserve(hass, entry.data, dt_util.utcnow())

    async def write(entity, value):
        await hass.services.async_call(
            "number", "set_value", {"entity_id": entity, "value": value}, blocking=True
        )

    runtime = Runtime(
        entry.options.get("mode", "shadow"),
        journal,
        read,
        write,
        evaluate=reader.refresh,
        writers=tuple(entry.data.get("reserve_entities", [])),
        leader=leader,
    )
    runtime.reader = reader
    runtime.applied_options = dict(entry.options)
    runtime.entry = entry
    runtime.hass = hass
    entry.runtime_data = runtime

    @callback
    def schedule(_event=None):
        if not runtime.closed:
            entry.async_create_background_task(hass, runtime.async_recalculate(), "ecoflow refresh")

    async def learn(_now=None):
        if runtime.closed or journal.blocked:
            return
        async with runtime._lock:
            try:
                await reader.learn()
            except ValueError, KeyError, HomeAssistantError, RuntimeError, TypeError:
                runtime.last_error = "learning_source_invalid"
            runtime.notify()

    async def stop(_event):
        await runtime.async_close(final=True)

    from homeassistant.exceptions import HomeAssistantError

    # Quarter-hour planner at :05 and minute safety at :00. Source state changes
    # use HA's event tracker and all requests serialize at the runtime lock.
    runtime.cancels.extend(
        [
            async_track_time_change(hass, schedule, minute=[0, 15, 30, 45], second=5),
            async_track_time_change(hass, schedule, second=0),
            async_track_time_change(hass, learn, minute=5, second=0),
            async_track_time_change(hass, learn, hour=0, minute=10, second=0),
            async_track_state_change_event(hass, reader.trigger_ids(), schedule),
            hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, stop),
            hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, learn),
        ]
    )

    async def updated(_hass, updated_entry):
        if runtime.applied_options != dict(updated_entry.options):
            await hass.config_entries.async_reload(updated_entry.entry_id)

    entry.async_on_unload(entry.add_update_listener(updated))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    # Setup itself stays entirely passive. Timers/events/explicit service perform
    # refresh after HA sources and Recorder are ready.
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    runtime = entry.runtime_data
    safe = await runtime.async_close()
    if not safe:
        # Persisted pending safety state must not disappear behind a successful UI unload.
        runtime.status = "recovery_blocked" if runtime.journal.blocked else "recovery_pending"
        runtime.notify()
        return False
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
