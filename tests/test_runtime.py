"""Safety tests for the only runtime writer."""
from __future__ import annotations

import unittest

from custom_components.ecoflow_smart_charge.runtime import Runtime


class FakeJournal:
    def __init__(self) -> None:
        self.events: list[str] = []
        self.record = None

    async def async_capture_before_command(self, _id, _before, _targets):
        self.events.append("persist")
        self.record = object()

    async def async_update_phase(self, phase, pending_targets=None):
        self.events.append(f"phase:{phase}")

    async def async_clear_after_readback(self):
        self.events.append("clear")
        self.record = None


class RuntimeSafetyTests(unittest.IsolatedAsyncioTestCase):
    async def test_shadow_never_invokes_writer(self) -> None:
        journal = FakeJournal()
        calls: list[tuple[str, float]] = []
        runtime = Runtime("shadow", journal, lambda entity: 3.0, lambda entity, value: calls.append((entity, value)))
        await runtime.async_start({"number.one": 3.0})
        self.assertEqual(calls, [])
        self.assertEqual(journal.events, [])

    async def test_active_persists_intent_before_any_writer_call(self) -> None:
        journal = FakeJournal()
        events: list[str] = []
        runtime = Runtime("active", journal, lambda entity: 3.0, lambda entity, value: events.append(f"write:{entity}"))
        await runtime.async_start({"number.one": 3.0})
        self.assertEqual(journal.events[0], "persist")
        self.assertEqual(events, ["write:number.one"])

    async def test_restore_clears_only_after_individual_readback(self) -> None:
        journal = FakeJournal()
        journal.record = type("Record", (), {"reserves_before": {"number.one": 3.0, "number.two": 4.0}})()
        values = {"number.one": 3.0, "number.two": 9.0}
        calls: list[tuple[str, float]] = []
        runtime = Runtime("active", journal, lambda entity: values[entity], lambda e, v: calls.append((e, v)))
        restored = await runtime.async_restore()
        self.assertFalse(restored)
        self.assertNotIn("clear", journal.events)
        self.assertEqual(calls, [("number.two", 4.0)])


if __name__ == "__main__":
    unittest.main()
