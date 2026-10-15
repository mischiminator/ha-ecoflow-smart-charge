"""Single serialized writer for reserve commands and recovery."""
from __future__ import annotations

import asyncio
import inspect
from collections.abc import Callable, Mapping
from typing import Any

from homeassistant.exceptions import HomeAssistantError


class Runtime:
    """All hardware intent passes here; shadow mode has no writer path."""

    def __init__(
        self,
        mode: str,
        journal: Any,
        read_reserve: Callable[[str], float],
        write_reserve: Callable[[str, float], Any],
    ) -> None:
        self.mode = mode
        self.journal = journal
        self._read = read_reserve
        self._write = write_reserve
        self._lock = asyncio.Lock()
        self.status = "shadow" if mode == "shadow" else "idle"

    async def async_start(self, reserves_before: Mapping[str, float]) -> bool:
        """Capture individual values before the first command, then request 100%."""
        async with self._lock:
            if self.mode != "active":
                self.status = "shadow"
                return False
            # A persisted intent is authoritative after a retry/reload.  Never replace
            # individual pre-session reserves with a later observation.
            if self.journal.record is not None:
                self.status = "recovery_pending"
                return False
            if not reserves_before or any(not 0 <= float(value) <= 100 for value in reserves_before.values()):
                self.status = "reserve_data_invalid"
                return False
            targets = {entity: 100.0 for entity in reserves_before}
            # This await is deliberately before every service request.
            await self.journal.async_capture_before_command("session", dict(reserves_before), targets)
            self.status = "charging_pending_readback"
            failed: dict[str, float] = {}
            for entity, target in targets.items():
                try:
                    await self._maybe_await(self._write(entity, target))
                except (HomeAssistantError, ValueError, TypeError):
                    # Device/service failures must remain recoverable.
                    failed[entity] = target
            if failed:
                await self.journal.async_update_phase("charge_pending", failed)
                self.status = "charge_pending"
                return False
            return True

    async def async_restore(self) -> bool:
        """Restore only non-confirmed individual reserves; clear only after readback."""
        async with self._lock:
            record = self.journal.record
            if record is None:
                return True
            pending: dict[str, float] = {}
            for entity, original in record.reserves_before.items():
                try:
                    actual = float(await self._maybe_await(self._read(entity)))
                except (TypeError, ValueError):
                    actual = float("nan")
                if actual != float(original):
                    pending[entity] = float(original)
            if pending:
                self.status = "recovery_pending"
                await self.journal.async_update_phase("restore_pending", pending)
                for entity, target in pending.items():
                    await self._maybe_await(self._write(entity, target))
                return False
            await self.journal.async_clear_after_readback()
            self.status = "restored"
            return True

    async def async_recalculate(self) -> None:
        """Record a shadow-safe recalculation request without issuing commands."""
        async with self._lock:
            self.status = "shadow_recalculated" if self.mode == "shadow" else "recalculated"

    async def async_request_cutover(self) -> None:
        """Fail closed until validated comparison and conflict gates are implemented."""
        async with self._lock:
            self.status = "cutover_not_safe"
            raise RuntimeError("cutover requires validated shadow comparison and conflict clearance")

    @staticmethod
    async def _maybe_await(value: Any) -> Any:
        if inspect.isawaitable(value):
            return await value
        return value
