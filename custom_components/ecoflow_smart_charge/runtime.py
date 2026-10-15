"""Single serialized executor: explicit ownership, durable intent, independent readback."""

from __future__ import annotations

import asyncio
import inspect
from datetime import UTC, datetime
from uuid import uuid4

from homeassistant.exceptions import HomeAssistantError

from .storage import finite


class Runtime:
    """No entity/service/timer may bypass this entry-local lock and executor."""

    def __init__(
        self,
        mode,
        journal,
        read_reserve,
        write_reserve,
        *,
        evaluate=None,
        writers=(),
        save_comparison=None,
    ):
        # Persisted options cannot reactivate a controller on restart.
        self.mode = "shadow"
        self.journal = journal
        self._read, self._write, self._evaluate = read_reserve, write_reserve, evaluate
        self.writers = tuple(writers)
        self._save_comparison = save_comparison
        self._lock = asyncio.Lock()
        self.status = (
            "recovery_blocked"
            if journal.blocked
            else ("recovery_pending" if journal.record else "shadow")
        )
        self.last_snapshot = None
        self.comparison = None
        self.authorized = False
        self.closed = False
        self.cancels = []
        self.listeners = set()
        self.last_error = None

    def subscribe(self, callback):
        self.listeners.add(callback)
        return lambda: self.listeners.discard(callback)

    def notify(self):
        for callback in tuple(self.listeners):
            callback()

    async def _gate(self):
        if self.closed or self.journal.blocked or self._evaluate is None:
            return {"owned": False, "valid": False, "allowed": False, "master": False}
        gate = await self._maybe_await(self._evaluate())
        self.last_snapshot = gate
        return gate

    def _mapping_valid(self):
        return (
            len(self.writers) == 3
            and len(set(self.writers)) == 3
            and (
                self.journal.record is None
                or set(self.journal.record.reserves_before) == set(self.writers)
            )
        )

    async def _reported(self, entity, desired):
        try:
            value, stamp = await self._maybe_await(self._read(entity))
            value = finite(float(value), 3)
            now = datetime.now(UTC)
            record = self.journal.record
            thresholds = [record.created_at, record.intent_at.get(entity, record.created_at)]
            if record.restore_started_at:
                thresholds.append(record.restore_started_at)
            created = max(datetime.fromisoformat(t) for t in thresholds)
            if (
                stamp.tzinfo is None
                or not 0 <= (now - stamp).total_seconds() < 120
                or stamp <= created
            ):
                return False
            if abs(value - desired) > 0.001:
                return False
            await self.journal.async_evidence(entity, value, stamp.isoformat())
            return True
        except TypeError, ValueError, AttributeError, KeyError:
            return False

    async def _execute(self, targets, *, restore):
        if self.mode == "shadow" or not self.authorized or not self._mapping_valid():
            self.status = "recovery_pending" if self.journal.record else "shadow"
            return False
        phase = "restore_pending" if restore else "charge_pending"
        if restore and self.journal.record.phase != "restore_pending":
            await self.journal.async_update_phase("restore_pending", targets)
        pending = {}
        for entity, target in targets.items():
            if not await self._reported(entity, target):
                pending[entity] = target
        await self.journal.async_update_phase(phase, pending)
        if not pending:
            if restore:
                await self.journal.async_clear_after_readback()
                self.status = "restored"
            else:
                await self.journal.async_update_phase("charging", {})
                self.status = "charging"
            return True
        self.status = phase
        for entity, target in pending.items():
            record = self.journal.record
            intent = record.intent_at.get(entity)
            if intent is not None:
                stamp = datetime.fromisoformat(intent)
                # Charge intents must never delay the first safety restoration.
                same_phase = record.intent_targets.get(entity) == target
                if same_phase and (datetime.now(UTC) - stamp).total_seconds() < 30:
                    continue
            gate = await self._gate()
            if not gate.get("owned") or (
                not restore and not all(gate.get(k) for k in ("valid", "allowed", "master"))
            ):
                self.status = "writer_conflict" if not gate.get("owned") else "charge_blocked"
                break
            await self.journal.async_intent(entity, target, phase)
            # Save yields to HA: recheck ownership and all charge gates again.
            gate = await self._gate()
            if self.mode == "shadow" or not self.authorized or not gate.get("owned"):
                break
            if not restore and not all(gate.get(k) for k in ("valid", "allowed", "master")):
                break
            try:
                async with asyncio.timeout(10):
                    await self._maybe_await(self._write(entity, target))
            except HomeAssistantError, ValueError, TypeError, TimeoutError, OSError:
                self.last_error = "device_command_failed"
        # Even an ACK with synchronous state update is only confirmed on next observation.
        return False

    async def async_start(self, reserves_before=None):
        async with self._lock:
            result = await self._start(reserves_before)
            self.notify()
            return result

    async def _start(self, reserves_before):
        gate = await self._gate()
        if self.mode != "active" or not self.authorized or not self._mapping_valid():
            return False
        if self.journal.record is not None:
            self.status = "recovery_pending"
            return False
        if not all(gate.get(k) for k in ("owned", "valid", "allowed", "master")):
            return False
        if reserves_before is None:
            reserves_before = {
                e: finite(float((await self._maybe_await(self._read(e)))[0]), 3)
                for e in self.writers
            }
        if set(reserves_before) != set(self.writers):
            return False
        try:
            originals = {e: finite(v, 3) for e, v in reserves_before.items()}
        except ValueError:
            return False
        await self.journal.async_capture_before_command(
            uuid4().hex, originals, {e: 100.0 for e in originals}, solar_day=gate.get("solar_day")
        )
        return await self._execute({e: 100.0 for e in originals}, restore=False)

    async def async_retry_charge(self):
        async with self._lock:
            record = self.journal.record
            if record is None or record.phase not in (
                "intent_persisted",
                "charge_pending",
                "charging",
            ):
                return False
            result = await self._execute({e: 100.0 for e in record.reserves_before}, restore=False)
            self.notify()
            return result

    async def _restore(self):
        record = self.journal.record
        if self.journal.blocked:
            self.status = "recovery_blocked"
            return False
        if record is None:
            return True
        if self.mode == "shadow":
            self.status = "recovery_pending"
            return False
        gate = await self._gate()
        if gate.get("full") and record.solar_day:
            await self.journal.async_set_marker(record.solar_day)
        return await self._execute(dict(record.reserves_before), restore=True)

    async def async_restore(self):
        async with self._lock:
            result = await self._restore()
            self.notify()
            return result

    async def async_recalculate(self):
        async with self._lock:
            gate = await self._gate()
            self.status = "recovery_pending" if self.journal.record else "shadow_recalculated"
            if self.mode == "active":
                record = self.journal.record
                if record and (
                    record.phase in ("restore_pending", "recovery_pending")
                    or gate.get("full")
                    or not all(gate.get(k) for k in ("valid", "allowed", "master", "owned"))
                ):
                    await self._restore()
                elif record:
                    await self._execute({e: 100.0 for e in record.reserves_before}, restore=False)
                else:
                    await self._start(None)
            self.notify()

    async def async_record_comparison(self, expected):
        async with self._lock:
            gate = await self._gate()
            if self.mode != "shadow" or not gate.get("valid") or not expected:
                raise ValueError("valid shadow plan required")
            allowed = {"allowed", "reason", "advantage", "net_saving", "profile_valid"}
            if set(expected) - allowed or any(gate.get(k) != v for k, v in expected.items()):
                raise ValueError("shadow comparison differs")
            # Require projected metrics as well as permission in the HA service schema.
            comparison = {"at": datetime.now(UTC).isoformat(), "expected": dict(expected)}
            if self._save_comparison is None:
                raise ValueError("comparison storage unavailable")
            await self._maybe_await(self._save_comparison(comparison))
            self.comparison = comparison
            self.notify()

    async def async_request_cutover(self, *, confirmed=False):
        async with self._lock:
            gate = await self._gate()
            age = (
                float("inf")
                if not self.comparison
                else (
                    datetime.now(UTC) - datetime.fromisoformat(self.comparison["at"])
                ).total_seconds()
            )
            if (
                not confirmed
                or self.mode != "shadow"
                or self.journal.record
                or self.journal.blocked
                or not self._mapping_valid()
                or not 0 <= age < 1200
                or not all(gate.get(k) for k in ("valid", "owned", "master"))
            ):
                self.status = "cutover_not_safe"
                raise ValueError(
                    "cutover requires confirmed fresh comparison, validity and exclusive ownership"
                )
            for entity in self.writers:
                try:
                    value, stamp = await self._maybe_await(self._read(entity))
                    finite(float(value), 3)
                    if not 0 <= (datetime.now(UTC) - stamp).total_seconds() < 120:
                        raise ValueError("stale reserve")
                except TypeError, AttributeError:
                    raise ValueError("unknown reserve") from None
            self.authorized = True
            self.mode = "active"
            self.status = "idle"
            self.notify()

    async def async_confirm_recovery(self, *, confirmed=False):
        async with self._lock:
            gate = await self._gate()
            if (
                not confirmed
                or self.mode != "shadow"
                or not gate.get("owned")
                or not self._mapping_valid()
                or self.journal.blocked
            ):
                raise ValueError("explicit exclusive recovery authorization required")
            self.mode = "recovery"
            self.authorized = True
            try:
                return await self._restore()
            finally:
                self.mode = "shadow"
                self.authorized = False
                self.notify()

    async def async_set_shadow(self):
        async with self._lock:
            # Stop under existing active ownership before switching; never switch to recovery automatically.
            try:
                if self.mode == "active" and self.journal.record:
                    await self._restore()
            finally:
                self.mode = "shadow"
                self.authorized = False
                self.comparison = None
                self.status = "recovery_pending" if self.journal.record else "shadow"
                self.notify()

    async def async_set_setting(self, key, value):
        from .config_flow import validate_settings

        validate_settings({key: value})
        async with self._lock:
            if key == "master" and not value and self.mode == "active":
                try:
                    if self.journal.record:
                        await self._restore()
                finally:
                    self.mode = "shadow"
                    self.authorized = False
                    self.comparison = None
                    self.status = "recovery_pending" if self.journal.record else "shadow"
                    self.notify()
            options = {**self.entry.options, key: value, "mode": "shadow"}
            self.applied_options = dict(options)
            self.hass.config_entries.async_update_entry(self.entry, options=options)
            self.notify()

    async def async_close(self):
        for cancel in self.cancels:
            cancel()
        self.cancels.clear()
        async with self._lock:
            try:
                if self.mode == "active" and self.journal.record:
                    await self._restore()
            finally:
                safe = not self.journal.blocked and self.journal.record is None
                self.closed = safe
                self.mode = "shadow"
                self.authorized = False
                self.comparison = None
                if not safe:
                    self.status = "recovery_blocked" if self.journal.blocked else "recovery_pending"
                self.notify()
            return safe

    @staticmethod
    async def _maybe_await(value):
        return await value if inspect.isawaitable(value) else value
