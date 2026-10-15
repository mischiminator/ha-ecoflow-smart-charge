"""Single serialized writer for reserve commands and recovery."""
from __future__ import annotations

import asyncio
import inspect
from collections.abc import Callable, Mapping
from typing import Any


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
            targets = {entity: 100.0 for entity in reserves_before}
            # This await is deliberately before every service request.
            await self.journal.async_capture_before_command("session", dict(reserves_before), targets)
            self.status = "charging_pending_readback"
            for entity, target in targets.items():
                await self._maybe_await(self._write(entity, target))
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

    @staticmethod
    async def _maybe_await(value: Any) -> Any:
        if inspect.isawaitable(value):
            return await value
        return value
