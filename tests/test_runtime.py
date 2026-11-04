"""Runtime construction fails closed to shadow for unknown modes."""

import pytest

from custom_components.ecoflow_smart_charge.runtime import Runtime
from custom_components.ecoflow_smart_charge.storage import PersistentSessionStore


class Disk:
    async def async_load(self):
        return None

    async def async_save(self, data):
        self.data = data


@pytest.mark.parametrize("requested_mode", ["shadow", "armed", "recovery", None])
async def test_unknown_constructor_mode_falls_back_to_shadow(requested_mode):
    journal = PersistentSessionStore(Disk())
    calls = []
    runtime = Runtime(requested_mode, journal, lambda _: 3, lambda *args: calls.append(args))
    assert runtime.mode == "shadow"
    assert not await runtime.async_start({"number.one": 3})
    assert calls == [] and journal.record is None


async def test_shadow_with_pending_journal_remains_visible_on_close():
    journal = PersistentSessionStore(Disk())
    await journal.async_capture_before_command("old", {"number.one": 13}, {"number.one": 100})
    calls = []
    runtime = Runtime("shadow", journal, lambda _: 100, lambda *args: calls.append(args))
    cancelled = []
    runtime.cancels.append(lambda: cancelled.append(True))
    assert not await runtime.async_close()
    assert journal.record is not None and calls == []
    # A failed unload keeps the timers that finish the restore.
    assert runtime.cancels and not cancelled
    await journal.async_clear_after_readback()
    assert await runtime.async_close()
    assert cancelled == [True] and not runtime.cancels
