"""Real lifecycle recovery and diagnostics redaction tests."""

from datetime import UTC, datetime

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ecoflow_smart_charge.const import DOMAIN


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_diagnostics_redact_entity_ids(hass):
    entry = MockConfigEntry(
        domain=DOMAIN, data={"reserve_entities": [f"number.reserve_{i}" for i in range(3)]}
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    from custom_components.ecoflow_smart_charge.diagnostics import (
        async_get_config_entry_diagnostics,
    )

    diagnostic = await async_get_config_entry_diagnostics(hass, entry)
    assert diagnostic["mode"] == "shadow"
    assert "number.reserve" not in str(diagnostic)
    assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_restart_pending_shadow_does_not_write_until_active_restores(hass, hass_storage):
    from dataclasses import asdict

    from custom_components.ecoflow_smart_charge.storage import SessionRecord

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "reserve_entities": [f"number.reserve_{i}" for i in range(3)],
        },
        options={"mode": "shadow"},
    )
    originals = {e: 13.0 + i for i, e in enumerate(entry.data["reserve_entities"])}
    record = SessionRecord(
        "prior", datetime.now(UTC).isoformat(), originals, {e: 100.0 for e in originals}
    )
    state = {
        "schema_version": 1,
        "session": asdict(record),
        "learning": {},
        "full_marker_day": None,
    }
    hass_storage[f"{DOMAIN}.{entry.entry_id}"] = {
        "version": 1,
        "minor_version": 1,
        "key": f"{DOMAIN}.{entry.entry_id}",
        "data": state,
    }
    for e in originals:
        hass.states.async_set(e, "100", {"unit_of_measurement": "%"})
    calls = []

    async def write(call):
        calls.append(call.data)

    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    # Replace only the physical transport AFTER HA platform registration.
    hass.services.async_register("number", "set_value", write)
    runtime = entry.runtime_data
    assert runtime.mode == "shadow" and runtime.journal.record
    await hass.services.async_call(
        DOMAIN, "recalculate", {"config_entry_id": entry.entry_id}, blocking=True
    )
    assert calls == []
    assert not await hass.config_entries.async_unload(entry.entry_id)
    assert calls == [] and runtime.journal.record
    # Switching to active restores the saved originals; sources are invalid here.
    await runtime.async_set_setting("mode", "active")
    await runtime.async_recalculate()
    assert len(calls) == 3 and runtime.mode == "active"
    assert entry.options["mode"] == "active"
    for e, v in originals.items():
        hass.states.async_set(e, str(v), {"unit_of_measurement": "%"})
    await runtime.async_recalculate()
    assert runtime.journal.record is None
    from homeassistant.config_entries import ConfigEntryState

    assert entry.state is ConfigEntryState.FAILED_UNLOAD
    # HA marks failed unload nonrecoverable; after recovery a restart is required.
    # Exercise component cleanup directly, not a fabricated manager state.
    from custom_components.ecoflow_smart_charge import async_unload_entry

    assert await async_unload_entry(hass, entry)
