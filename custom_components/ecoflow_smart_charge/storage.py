"""Awaited versioned intent journal. Store completion is not hardware readback."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field, replace
from datetime import UTC, date, datetime
from math import isfinite
from typing import Any, Protocol
from uuid import uuid4

PHASES = {"intent_persisted", "charge_pending", "charging", "restore_pending", "recovery_pending"}


def finite(value, low=0, high=100):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("invalid numeric value")  # noqa: TRY004 - one validation error contract
    if not isfinite(value) or not low <= value <= high:
        raise ValueError("out of range")
    return float(value)


def iso_day(value):
    if value is not None and (
        not isinstance(value, str) or date.fromisoformat(value).isoformat() != value
    ):
        raise ValueError("invalid day")
    return value


@dataclass(frozen=True)
class SessionRecord:
    session_id: str
    created_at: str
    reserves_before: dict[str, float]
    pending_targets: dict[str, float]
    phase: str = "intent_persisted"
    full_marker_day: str | None = None
    command_ids: dict[str, str] = field(default_factory=dict)
    readback: dict[str, dict] = field(default_factory=dict)
    solar_day: str | None = None
    intent_at: dict[str, str] = field(default_factory=dict)
    restore_started_at: str | None = None
    intent_targets: dict[str, float] = field(default_factory=dict)


class StoreProtocol(Protocol):
    async def async_load(self) -> dict[str, Any] | None: ...
    async def async_save(self, data: dict[str, Any]) -> None: ...


def validate_session(raw):
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise ValueError("invalid session object")  # noqa: TRY004 - one validation error contract
    record = SessionRecord(**raw)
    created = datetime.fromisoformat(record.created_at)
    if (
        not isinstance(record.session_id, str)
        or not record.session_id
        or created.tzinfo is None
        or record.phase not in PHASES
    ):
        raise ValueError("invalid session")
    if (
        not isinstance(record.reserves_before, dict)
        or not record.reserves_before
        or len(record.reserves_before) > 3
    ):
        raise ValueError("invalid mapping")
    if not isinstance(record.pending_targets, dict):
        raise ValueError("invalid targets")  # noqa: TRY004 - one validation error contract
    for entity, value in record.reserves_before.items():
        if not isinstance(entity, str) or not entity.startswith("number."):
            raise ValueError("invalid writer")
        finite(value, 3)
    for entity, value in record.pending_targets.items():
        if entity not in record.reserves_before:
            raise ValueError("unknown target")
        finite(value, 3)
    if set(record.command_ids) - set(record.reserves_before) or set(record.readback) - set(
        record.reserves_before
    ):
        raise ValueError("unknown evidence")
    iso_day(record.solar_day)
    iso_day(record.full_marker_day)
    for mapping in (record.command_ids, record.intent_at, record.readback, record.intent_targets):
        if not isinstance(mapping, dict) or set(mapping) - set(record.reserves_before):
            raise ValueError("invalid command evidence")
    if any(not isinstance(v, str) or not v for v in record.command_ids.values()):
        raise ValueError("invalid command id")
    for stamp in [
        *record.intent_at.values(),
        *([record.restore_started_at] if record.restore_started_at else []),
    ]:
        if not isinstance(stamp, str) or datetime.fromisoformat(stamp).tzinfo is None:
            raise ValueError("invalid intent timestamp")
    for target in record.intent_targets.values():
        finite(target, 3)
    for evidence in record.readback.values():
        if not isinstance(evidence, dict) or set(evidence) != {"value", "at"}:
            raise ValueError("invalid readback")
        finite(evidence["value"], 3)
        if (
            not isinstance(evidence["at"], str)
            or datetime.fromisoformat(evidence["at"]).tzinfo is None
        ):
            raise ValueError("invalid readback timestamp")
    return record


def validate_learning(raw):
    if not isinstance(raw, dict) or set(raw) - {
        "ratios",
        "correction",
        "probe_day",
        "probe_kwh",
        "learned_day",
    }:
        raise ValueError("invalid learning state")
    result = {
        "ratios": [],
        "correction": 1.0,
        "probe_day": None,
        "probe_kwh": None,
        "learned_day": None,
        **raw,
    }
    if not isinstance(result["ratios"], (list, tuple)) or len(result["ratios"]) > 14:
        raise ValueError("invalid ratios")
    result["ratios"] = [finite(v, 0, 5) for v in result["ratios"]]
    finite(result["correction"], 0, 5)
    iso_day(result["probe_day"])
    iso_day(result["learned_day"])
    if result["probe_kwh"] is not None:
        finite(result["probe_kwh"], 0, 1000)
    if (result["probe_day"] is None) != (result["probe_kwh"] is None):
        raise ValueError("incomplete probe")
    return result


class PersistentSessionStore:
    """Never commit memory before save. Malformed records remain blocked on disk."""

    def __init__(self, store: StoreProtocol, *, expected_exists=False):
        self._store = store
        self.expected_exists = expected_exists
        self.record = None
        self.learning = validate_learning({})
        self.full_marker_day = None
        self.blocked = False

    def envelope(self, record=None, **changes):
        return {
            "schema_version": 1,
            "session": asdict(record) if record else None,
            "learning": deepcopy(self.learning),
            "full_marker_day": self.full_marker_day,
            **changes,
        }

    async def async_load(self):
        try:
            raw = await self._store.async_load()
            if raw is None:  # New store only; {} is not treated as safe empty state.
                if self.expected_exists:
                    self.blocked = True
                return None
            if (
                not isinstance(raw, dict)
                or type(raw.get("schema_version")) is not int
                or raw.get("schema_version") != 1
            ):
                raise ValueError("unsupported envelope; explicit import required")
            if set(raw) != {"schema_version", "session", "learning", "full_marker_day"}:
                raise ValueError("incomplete envelope")
            record = validate_session(raw["session"])
            learning = validate_learning(raw["learning"])
            marker = iso_day(raw["full_marker_day"])
        except ValueError, TypeError, KeyError, OSError:
            self.blocked = True
            return None
        self.record, self.learning, self.full_marker_day = record, learning, marker
        return record

    async def _save(self, record, **changes):
        if self.blocked:
            raise ValueError("journal recovery blocked")
        await self._store.async_save(self.envelope(record, **changes))
        self.record = record
        for key, value in changes.items():
            setattr(self, key, deepcopy(value))

    async def async_capture_before_command(
        self, session_id, reserves_before, targets, *, solar_day=None
    ):
        if self.record is not None:
            raise ValueError("existing session")
        record = validate_session(
            asdict(
                SessionRecord(
                    session_id,
                    datetime.now(UTC).isoformat(),
                    dict(reserves_before),
                    dict(targets),
                    solar_day=solar_day,
                )
            )
        )
        await self._save(record)
        return record

    async def async_update_phase(self, phase, pending_targets=None):
        if self.record is None or phase not in PHASES:
            raise ValueError("invalid phase")
        record = replace(
            self.record,
            phase=phase,
            pending_targets=dict(
                self.record.pending_targets if pending_targets is None else pending_targets
            ),
        )
        if phase == "restore_pending" and record.restore_started_at is None:
            record = replace(record, restore_started_at=datetime.now(UTC).isoformat())
        await self._save(record)

    async def async_intent(self, entity, target, phase):
        if self.record is None:
            raise ValueError("no session")
        ids = {**self.record.command_ids, entity: uuid4().hex}
        await self._save(
            replace(
                self.record,
                phase=phase,
                pending_targets={**self.record.pending_targets, entity: target},
                command_ids=ids,
                intent_at={**self.record.intent_at, entity: datetime.now(UTC).isoformat()},
                intent_targets={**self.record.intent_targets, entity: target},
            )
        )

    async def async_evidence(self, entity, value, stamp):
        record = self.record
        if record is None:
            raise ValueError("no session")
        await self._save(
            replace(record, readback={**record.readback, entity: {"value": value, "at": stamp}})
        )

    async def async_set_marker(self, day):
        await self._save(self.record, full_marker_day=iso_day(day))

    async def async_set_learning(self, learning):
        await self._save(self.record, learning=validate_learning(learning))

    async def async_clear_after_readback(self):
        await self._save(None)
