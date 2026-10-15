"""Absolute shadow regression against a real journal."""

import pytest

from custom_components.ecoflow_smart_charge.runtime import Runtime
from custom_components.ecoflow_smart_charge.storage import PersistentSessionStore


class MemoryStore:
    async def async_save(self, data):
        self.data = data

    async def async_load(self):
        return getattr(self, "data", None)


@pytest.mark.asyncio
async def test_pending_shadow_restore_never_calls_hardware():
    journal = PersistentSessionStore(MemoryStore())
    await journal.async_capture_before_command("prior", {"number.test": 17}, {"number.test": 100})
    calls = []
    runtime = Runtime("shadow", journal, lambda _: 100, lambda *args: calls.append(args))
    assert not await runtime.async_restore()
    assert calls == []
    assert journal.record is not None
