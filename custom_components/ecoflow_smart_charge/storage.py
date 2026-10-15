"""Crash-safe session journal backed by HA Store at the adapter boundary."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Protocol


@dataclass(frozen=True)
class SessionRecord:
    session_id: str
    created_at: str
    reserves_before: dict[str, float]
    pending_targets: dict[str, float]
    phase: str = "intent_persisted"
    full_marker_day: str | None = None


class StoreProtocol(Protocol):
    async def async_load(self) -> dict[str, Any] | None: ...
    async def async_save(self, data: dict[str, Any]) -> None: ...


class PersistentSessionStore:
    """Store only integration-owned safety state; never entity credentials or raw history."""

    def __init__(self, store: StoreProtocol) -> None:
        self._store = store
        self.record: SessionRecord | None = None

    async def async_load(self) -> SessionRecord | None:
        raw = await self._store.async_load()
        if not raw:
            return None
        try:
            self.record = SessionRecord(**raw)
        except (TypeError, ValueError):
            self.record = None
        return self.record

    async def async_capture_before_command(
        self, session_id: str, reserves_before: dict[str, float], targets: dict[str, float]
    ) -> SessionRecord:
        """Durably save intent before any reserve service call is permitted."""
        record = SessionRecord(
            session_id=session_id,
            created_at=datetime.now().astimezone().isoformat(),
            reserves_before=dict(reserves_before),
            pending_targets=dict(targets),
        )
        await self._store.async_save(asdict(record))
        self.record = record
        return record

    async def async_update_phase(self, phase: str, pending_targets: dict[str, float] | None = None) -> None:
        if self.record is None:
            raise RuntimeError("no persisted session")
        self.record = SessionRecord(
            session_id=self.record.session_id,
            created_at=self.record.created_at,
            reserves_before=self.record.reserves_before,
            pending_targets=pending_targets if pending_targets is not None else self.record.pending_targets,
            phase=phase,
            full_marker_day=self.record.full_marker_day,
        )
        await self._store.async_save(asdict(self.record))

    async def async_clear_after_readback(self) -> None:
        if self.record is None:
            return
        await self._store.async_save({})
        self.record = None
