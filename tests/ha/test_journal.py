"""Durable safety-state boundary tests; synthetic individual reserves."""

from copy import deepcopy

import pytest

from custom_components.ecoflow_smart_charge.storage import PersistentSessionStore


class MemoryStore:
    def __init__(self):
        self.data = None
        self.fail = False

    async def async_load(self):
        return deepcopy(self.data)

    async def async_save(self, data):
        if self.fail:
            raise OSError("disk unavailable")
        self.data = deepcopy(data)


@pytest.mark.asyncio
async def test_invalid_journal_is_blocked_not_silently_discarded():
    backend = MemoryStore()
    backend.data = {"schema_version": 999, "session": None}
    journal = PersistentSessionStore(backend)
    await journal.async_load()
    assert journal.blocked
    assert backend.data["schema_version"] == 999


@pytest.mark.asyncio
async def test_failed_phase_save_does_not_commit_memory():
    backend = MemoryStore()
    journal = PersistentSessionStore(backend)
    await journal.async_capture_before_command("test", {"number.a": 11}, {"number.a": 100})
    before = journal.record
    backend.fail = True
    with pytest.raises(OSError):
        await journal.async_update_phase("restore_pending", {"number.a": 11})
    assert journal.record == before


@pytest.mark.asyncio
async def test_marker_survives_session_clear():
    backend = MemoryStore()
    journal = PersistentSessionStore(backend)
    await journal.async_capture_before_command("test", {"number.a": 11}, {"number.a": 100})
    await journal.async_set_marker("2026-01-04")
    await journal.async_clear_after_readback()
    loaded = PersistentSessionStore(backend)
    await loaded.async_load()
    assert loaded.record is None
    assert loaded.full_marker_day == "2026-01-04"


@pytest.mark.parametrize(
    "field,value",
    [
        ("reserves_before", [11, 12, 13]),
        ("reserves_before", {7: 11}),
        ("pending_targets", []),
        ("readback", {"number.a": {"value": 11, "at": "not-a-date"}}),
        ("readback", {"number.a": {"value": True, "at": "2026-01-04T12:00:00+00:00"}}),
        ("intent_at", {"number.a": "2026-01-04T12:00:00"}),
    ],
)
async def test_malformed_safety_fields_block_without_modifying_disk(field, value):
    backend = MemoryStore()
    journal = PersistentSessionStore(backend)
    await journal.async_capture_before_command("test", {"number.a": 11}, {"number.a": 100})
    backend.data["session"][field] = value
    before = deepcopy(backend.data)
    loaded = PersistentSessionStore(backend)
    await loaded.async_load()
    assert loaded.blocked
    assert loaded.record is None
    assert backend.data == before
