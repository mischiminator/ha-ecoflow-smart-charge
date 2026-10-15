"""Fail-closed runtime indicators."""

from homeassistant.components.binary_sensor import BinarySensorEntity

from .entity import RuntimeEntity

KEYS = {
    "shadow_active": "Shadow active",
    "recovery_pending": "Recovery pending",
    "session_active": "Charging session active",
    "sources_valid": "Sources valid",
    "writer_locked": "Writer locked",
    "permission": "Charge permission",
}


class GateSensor(RuntimeEntity, BinarySensorEntity):
    @property
    def is_on(self):
        gate = self.runtime.last_snapshot or {}
        if self.key == "session_active":
            return (
                self.runtime.journal.record is not None
                and self.runtime.journal.record.phase
                in ("charging", "charge_pending", "intent_persisted")
            )
        if self.key == "shadow_active":
            return self.runtime.mode == "shadow"
        if self.key == "recovery_pending":
            return self.runtime.journal.record is not None or self.runtime.journal.blocked
        if self.key == "sources_valid":
            return bool(gate.get("valid"))
        if self.key == "writer_locked":
            return not gate.get("owned", False)
        return bool(
            gate.get("allowed") and gate.get("valid") and gate.get("master") and gate.get("owned")
        )


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([GateSensor(entry, key, name) for key, name in KEYS.items()])
