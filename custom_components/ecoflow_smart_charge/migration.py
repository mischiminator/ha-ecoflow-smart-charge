"""Supported preview/import service. No storage-file edits and no device commands."""

from copy import deepcopy

from .config_flow import SETTINGS, validate_settings
from .storage import iso_day, validate_learning, validate_session


def validate_import(payload, writers):
    if (
        not isinstance(payload, dict)
        or set(payload) != {"schema_version", "settings", "learning", "session", "full_marker_day"}
        or type(payload["schema_version"]) is not int
        or payload["schema_version"] != 1
    ):
        raise ValueError("invalid_import_envelope")
    settings = validate_settings(payload["settings"])
    # Migration never silently supplies economic defaults or a master permission.
    if set(settings) != set(SETTINGS) | {"master", "mode"}:
        raise ValueError("complete_settings_required")
    learning = validate_learning(payload["learning"])
    marker = iso_day(payload["full_marker_day"])
    session = validate_session(payload["session"])
    if session is not None and (
        len(session.reserves_before) != 3 or set(session.reserves_before) != set(writers)
    ):
        raise ValueError("session_mapping_mismatch")
    return settings, learning, marker, session


async def async_import_state(hass, entry, payload, *, apply=False):
    runtime = entry.runtime_data
    async with runtime._lock:
        if (
            runtime.mode != "shadow"
            or runtime.journal.record is not None
            or runtime.journal.blocked
        ):
            raise ValueError("existing_safety_state_blocks_import")
        settings, learning, marker, session = validate_import(payload, runtime.writers)
        preview = {
            "schema_version": 1,
            "pending_session": session is not None,
            "ratio_count": len(learning["ratios"]),
            "settings": deepcopy(settings),
            "full_marker_day": marker,
            "applied": False,
        }
        if not apply:
            return preview
        # Journal must succeed before config-entry options; partial failure leaves
        # conservative recoverable shadow/session state, never a command.
        await runtime.journal._save(session, learning=learning, full_marker_day=marker)
        runtime.applied_options = dict(settings)
        hass.config_entries.async_update_entry(entry, options=settings)
        runtime.comparison = None
        runtime.status = "recovery_pending" if session else "shadow"
        runtime.notify()
        preview["applied"] = True
        return preview
