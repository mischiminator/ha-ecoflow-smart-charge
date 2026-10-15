"""Legacy runtime facade now fails closed without an explicitly authorized adapter."""

import pytest

from custom_components.ecoflow_smart_charge.runtime import Runtime
from custom_components.ecoflow_smart_charge.storage import PersistentSessionStore


class Disk:
    async def async_load(self):
        return None

    async def async_save(self, data):
        self.data = data


@pytest.mark.parametrize("requested_mode", ["shadow", "armed", "active", "recovery"])
async def test_constructor_mode_cannot_authorize_a_device_writer(requested_mode):
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
    assert not await runtime.async_close()
    assert journal.record is not None and calls == []
