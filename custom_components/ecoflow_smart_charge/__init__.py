"""Integration lifecycle and explicitly targeted services, using supported HA APIs."""

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
    from homeassistant.core import SupportsResponse
    from homeassistant.exceptions import ServiceValidationError

    target = {vol.Required("config_entry_id"): str}
    schemas = {
        "recalculate": vol.Schema(target),
        "request_cutover": vol.Schema(
            {
                **target,
                vol.Required("confirmed"): bool,
                vol.Required("commissioning_confirmed"): bool,
            }
        ),
        "confirm_recovery": vol.Schema({**target, vol.Required("confirmed"): bool}),
        "record_shadow_comparison": vol.Schema(
            {
                **target,
                vol.Required("expected"): vol.Schema(
                    {
                        vol.Required("allowed"): bool,
                        vol.Required("reason"): str,
                        vol.Required("profile_valid"): bool,
                        vol.Required("advantage"): vol.Any(None, vol.Coerce(float)),
                        vol.Required("net_saving"): vol.Coerce(float),
                    }
                ),
            }
        ),
        "import_state": vol.Schema(
            {**target, vol.Required("payload"): dict, vol.Optional("apply", default=False): bool}
        ),
    }

    async def handle(call):
        entry = hass.config_entries.async_get_entry(call.data["config_entry_id"])
        if entry is None or entry.domain != DOMAIN or getattr(entry, "runtime_data", None) is None:
            raise ServiceValidationError("configured controller entry is unavailable")
        runtime = entry.runtime_data
        try:
            if call.service == "recalculate":
                await runtime.async_recalculate()
            elif call.service == "request_cutover":
                await runtime.async_request_cutover(
                    confirmed=call.data["confirmed"],
                    commissioning_confirmed=call.data["commissioning_confirmed"],
                )
            elif call.service == "confirm_recovery":
                await runtime.async_confirm_recovery(confirmed=call.data["confirmed"])
            elif call.service == "record_shadow_comparison":
                await runtime.async_record_comparison(call.data["expected"])
            elif call.service == "import_state":
                from .migration import async_import_state

                return await async_import_state(
                    hass, entry, call.data["payload"], apply=call.data["apply"]
                )
        except (ValueError, OSError, RuntimeError) as err:
            raise ServiceValidationError(
                "controller request rejected: " + type(err).__name__
            ) from err
        return None

    for service, schema in schemas.items():
        if not hass.services.has_service(DOMAIN, service):
            hass.services.async_register(
                DOMAIN,
                service,
                handle,
                schema=schema,
                supports_response=SupportsResponse.OPTIONAL
                if service == "import_state"
                else SupportsResponse.NONE,
            )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    from homeassistant.const import EVENT_HOMEASSISTANT_STARTED, EVENT_HOMEASSISTANT_STOP
    from homeassistant.core import callback
    from homeassistant.helpers.event import async_track_state_change_event, async_track_time_change
    from homeassistant.helpers.storage import Store

    from .reader import SourceReader
    from .runtime import Runtime
    from .storage import PersistentSessionStore

    journal = PersistentSessionStore(
        Store(hass, STORE_VERSION, f"{DOMAIN}.{entry.entry_id}"),
        expected_exists=entry.data.get("journal_initialized", False),
    )
    await journal.async_load()
    if not entry.data.get("journal_initialized", False) and not journal.blocked:
        await journal._save(journal.record)
        hass.config_entries.async_update_entry(
            entry, data={**entry.data, "journal_initialized": True}
        )
    reader = SourceReader(hass, entry, journal)

    async def read(entity):
        state = hass.states.get(entity)
        return (state.state, state.last_reported) if state else (None, None)

    async def write(entity, value):
        await hass.services.async_call(
            "number", "set_value", {"entity_id": entity, "value": value}, blocking=True
        )

    comparison_store = Store(hass, 1, f"{DOMAIN}.{entry.entry_id}.comparison")
    runtime = Runtime(
        "shadow",
        journal,
        read,
        write,
        evaluate=reader.refresh,
        writers=tuple(entry.data.get("reserve_entities", [])),
        save_comparison=comparison_store.async_save,
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
        await runtime.async_close()

    from homeassistant.exceptions import HomeAssistantError

    # Quarter-hour planner at :05 and minute safety at :00. Source state changes
    # use HA's event tracker and all requests serialize at the runtime lock.
    runtime.cancels.extend(
        [
            async_track_time_change(hass, schedule, minute=[0, 15, 30, 45], second=5),
            async_track_time_change(hass, schedule, second=0),
            async_track_time_change(hass, learn, minute=5, second=0),
            async_track_time_change(hass, learn, hour=0, minute=10, second=0),
            async_track_state_change_event(hass, reader.selected_ids(), schedule),
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
    # refresh after HA sources and Recorder are ready. Restart always remains shadow.
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
