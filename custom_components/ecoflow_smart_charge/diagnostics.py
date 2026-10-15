"""Safe diagnostics: summary only, no raw entity IDs, attributes, or histories."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ConfigEntry) -> dict:
    runtime = entry.runtime_data
    record = getattr(getattr(runtime, "journal", None), "record", None)
    return {
        "entry_id": entry.entry_id,
        "mode": getattr(runtime, "mode", "unknown"),
        "status": getattr(runtime, "status", "unknown"),
        "recovery_pending": record is not None,
        "session_phase": getattr(record, "phase", None),
        "configured_source_count": len(entry.data),
        "domain": DOMAIN,
    }
