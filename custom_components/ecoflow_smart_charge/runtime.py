"""Single serialized executor: durable intent, independent readback."""

from __future__ import annotations

import asyncio
import inspect
from datetime import UTC, datetime
from uuid import uuid4

from homeassistant.exceptions import HomeAssistantError

from .planner.core import MAX_BATTERIES
from .storage import finite

# Forecasts move every quarter hour; smaller target changes are not worth a command.
RETARGET_POINTS = 2.0
# EcoFlow syncs a master's reserve to its slaves within seconds and reports only changes.
UNCHANGED_GRACE = 120


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
        leader=None,
    ):
        # Shadow is a test mode: plan only, never send hardware commands.
        self.mode = mode if mode in ("shadow", "active") else "shadow"
        self.journal = journal
        self._read, self._write, self._evaluate = read_reserve, write_reserve, evaluate
        self.writers = tuple(writers)
        # Returns the master's reserve entity, or None when no single master is known.
        self._leader = leader
        self._lock = asyncio.Lock()
        self.status = "recovery_blocked" if journal.blocked else self._idle_status()
        self.last_snapshot = None
        self.closed = False
        # Set by a failed unload: the timers may only finish the restore, never start anew.
        self.draining = False
        self.cancels = []
        self.listeners = set()
        self.last_error = None

    def subscribe(self, callback):
        self.listeners.add(callback)
        return lambda: self.listeners.discard(callback)

    def notify(self):
        for callback in tuple(self.listeners):
            callback()

    def _idle_status(self):
        if self.journal.record:
            return "recovery_pending"
        return "shadow" if self.mode == "shadow" else "idle"

    async def _gate(self):
        if self.closed or self.journal.blocked or self._evaluate is None:
            return {"valid": False, "allowed": False, "master": False}
        gate = await self._maybe_await(self._evaluate())
        self.last_snapshot = gate
        return gate

    def _mapping_valid(self):
        return (
            1 <= len(self.writers) <= MAX_BATTERIES
            and len(set(self.writers)) == len(self.writers)
            and (
                self.journal.record is None
                or set(self.journal.record.reserves_before) == set(self.writers)
            )
        )

    async def _reported(self, entity, desired, *, unchanged_ok=False):
        try:
            value, stamp = await self._maybe_await(self._read(entity))
            value = finite(float(value), 3)
            now = datetime.now(UTC)
            record = self.journal.record
            thresholds = [record.created_at, record.intent_at.get(entity, record.created_at)]
            if record.restore_started_at:
                thresholds.append(record.restore_started_at)
            created = max(datetime.fromisoformat(t) for t in thresholds)
            if stamp.tzinfo is None or abs(value - desired) > 0.001:
                return False
            # Any report after the intent proves the value; EcoFlow never repeats unchanged ones.
            if stamp > now or stamp <= created:
                # A restore value the device has shown since before the session, without any
                # report since, was never changed by it (EcoFlow reports only changes).
                session = datetime.fromisoformat(record.created_at)
                started = record.restore_started_at
                if not (
                    unchanged_ok
                    and stamp < session
                    and started
                    and (now - datetime.fromisoformat(started)).total_seconds() >= UNCHANGED_GRACE
                ):
                    return False
            await self.journal.async_evidence(entity, value, stamp.isoformat())
            return True
        except TypeError, ValueError, AttributeError, KeyError:
            return False

    async def _execute(self, targets, *, restore):
        if self.mode != "active" or not self._mapping_valid():
            self.status = self._idle_status()
            return False
        phase = "restore_pending" if restore else "charge_pending"
        if restore and self.journal.record.phase != "restore_pending":
            await self.journal.async_update_phase("restore_pending", targets)
        leader = self._leader() if self._leader else None
        leader = leader if leader in targets else None
        # The batteries sync one reserve: the master is commanded, its slaves confirm it.
        confirm = [e for e in targets if e != leader] or list(targets)
        pending = {}
        for entity in confirm:
            if not await self._reported(entity, targets[entity], unchanged_ok=restore):
                pending[entity] = targets[entity]
        if not pending:
            if restore:
                await self.journal.async_clear_after_readback()
                self.status = "restored"
            else:
                await self.journal.async_update_phase("charging", {})
                self.status = "charging"
            return True
        await self.journal.async_update_phase(phase, pending)
        self.status = phase
        commands = {leader: targets[leader]} if leader else pending
        for entity, target in commands.items():
            record = self.journal.record
            intent = record.intent_at.get(entity)
            if intent is not None:
                stamp = datetime.fromisoformat(intent)
                # Charge intents must never delay the first safety restoration.
                same_phase = record.intent_targets.get(entity) == target
                if same_phase and (datetime.now(UTC) - stamp).total_seconds() < 30:
                    continue
            if not restore and not await self._charge_allowed():
                self.status = "charge_blocked"
                break
            await self.journal.async_intent(entity, target, phase)
            # Save yields to HA: recheck all charge gates again.
            if not restore and not await self._charge_allowed():
                break
            try:
                async with asyncio.timeout(10):
                    await self._maybe_await(self._write(entity, target))
            except HomeAssistantError, ValueError, TypeError, TimeoutError, OSError:
                self.last_error = "device_command_failed"
        # Even an ACK with synchronous state update is only confirmed on next observation.
        return False

    def _charge_targets(self):
        record = self.journal.record
        return dict(record.charge_targets) or {e: 100.0 for e in record.reserves_before}

    async def _continue_charge(self, gate):
        """Follow the latest plan's shared target; reserves never drop below the originals."""
        current = self._charge_targets()
        originals = self.journal.record.reserves_before
        try:
            planned = gate["targets"]
            wanted = {e: max(finite(planned[e], 3), originals[e]) for e in originals}
        except KeyError, TypeError, ValueError:
            wanted = current
        if any(abs(wanted[e] - current[e]) >= RETARGET_POINTS for e in originals):
            await self.journal.async_set_charge_targets(wanted)
            current = wanted
        return await self._execute(current, restore=False)

    async def _charge_allowed(self):
        gate = await self._gate()
        return all(gate.get(k) for k in ("valid", "allowed", "master"))

    async def async_start(self, reserves_before=None):
        async with self._lock:
            result = await self._start(reserves_before)
            self.notify()
            return result

    async def _start(self, reserves_before):
        gate = await self._gate()
        if self.draining or self.mode != "active" or not self._mapping_valid():
            return False
        if self.journal.record is not None:
            self.status = "recovery_pending"
            return False
        if not all(gate.get(k) for k in ("valid", "allowed", "master")):
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
            planned = gate.get("targets") or dict.fromkeys(originals, 100.0)
            # Never lower a reserve below the user's own setting while charging.
            targets = {e: max(finite(planned[e], 3), originals[e]) for e in originals}
        except KeyError, TypeError, ValueError:
            return False
        if all(targets[e] <= originals[e] for e in originals):
            return False
        await self.journal.async_capture_before_command(
            uuid4().hex, originals, targets, solar_day=gate.get("solar_day")
        )
        return await self._execute(targets, restore=False)

    async def async_retry_charge(self):
        async with self._lock:
            record = self.journal.record
            if record is None or record.phase not in (
                "intent_persisted",
                "charge_pending",
                "charging",
            ):
                return False
            result = await self._execute(self._charge_targets(), restore=False)
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
            self.status = self._idle_status()
            if self.mode == "active":
                record = self.journal.record
                if record and (
                    record.phase in ("restore_pending", "recovery_pending")
                    or gate.get("full")
                    or not all(gate.get(k) for k in ("valid", "allowed", "master"))
                ):
                    await self._restore()
                elif record:
                    await self._continue_charge(gate)
                else:
                    await self._start(None)
            self.notify()

    async def async_set_setting(self, key, value):
        from .config_flow import validate_settings

        validate_settings({key: value})
        async with self._lock:
            try:
                stopping = (key == "master" and not value) or (key == "mode" and value == "shadow")
                if stopping and self.mode == "active" and self.journal.record:
                    # Restore under active control first; shadow never writes.
                    await self._restore()
            finally:
                if key == "mode":
                    self.mode = value
                    self.status = self._idle_status()
                options = {**self.entry.options, key: value}
                self.applied_options = dict(options)
                self.hass.config_entries.async_update_entry(self.entry, options=options)
                self.notify()

    async def async_close(self, *, final=False):
        async with self._lock:
            try:
                if self.mode == "active" and self.journal.record:
                    await self._restore()
            finally:
                safe = not self.journal.blocked and self.journal.record is None
                self.closed = safe
                self.draining = not safe
                # After a failed unload the timers confirm or repeat the restore; at HA stop
                # the journal carries it over the restart instead.
                if safe or final:
                    for cancel in self.cancels:
                        cancel()
                    self.cancels.clear()
                if not safe:
                    self.status = "recovery_blocked" if self.journal.blocked else "recovery_pending"
                self.notify()
            return safe

    @staticmethod
    async def _maybe_await(value):
        return await value if inspect.isawaitable(value) else value
