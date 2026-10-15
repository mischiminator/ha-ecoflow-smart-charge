"""Adversarial service/import/storage validation and real lifecycle recovery tests."""

from datetime import UTC, datetime

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ecoflow_smart_charge.const import DOMAIN


def payload():
    return {
        "schema_version": 1,
        "session": None,
        "learning": {
            "ratios": [0.8, 1, 1.2],
            "correction": 1.0,
            "probe_day": "2026-01-04",
            "probe_kwh": 4.0,
            "learned_day": "2026-01-03",
        },
        "full_marker_day": "2026-01-03",
        "settings": {
            "mode": "shadow",
            "master": True,
            "minimum_price_advantage_percent": 37.0,
            "charge_ceiling_ct": 29.0,
            "efficiency": 0.9,
            "wear_cost_ct": 1.0,
            "minimum_net_saving_ct": 2.0,
            "capacity_kwh": 3.0,
        },
    }


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_supported_import_preview_apply_and_diagnostics_redaction(hass):
    entry = MockConfigEntry(
        domain=DOMAIN, data={"reserve_entities": [f"number.reserve_{i}" for i in range(3)]}
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    before = dict(entry.options)
    preview = await hass.services.async_call(
        DOMAIN,
        "import_state",
        {"config_entry_id": entry.entry_id, "payload": payload()},
        blocking=True,
        return_response=True,
    )
    assert not preview["applied"] and dict(entry.options) == before
    result = await hass.services.async_call(
        DOMAIN,
        "import_state",
        {"config_entry_id": entry.entry_id, "payload": payload(), "apply": True},
        blocking=True,
        return_response=True,
    )
    assert result["applied"] and entry.options["minimum_price_advantage_percent"] == 37
    assert entry.options["charge_ceiling_ct"] == 29
    assert entry.runtime_data.mode == "shadow"
    from custom_components.ecoflow_smart_charge.diagnostics import (
        async_get_config_entry_diagnostics,
    )

    diagnostic = await async_get_config_entry_diagnostics(hass, entry)
    assert "number.reserve" not in str(diagnostic)
    assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.parametrize("bad", [True, 2, None, "1"])
async def test_import_schema_version_is_exact_integer(bad):
    from custom_components.ecoflow_smart_charge.migration import validate_import

    data = payload()
    data["schema_version"] = bad
    with pytest.raises(ValueError):
        validate_import(data, ())


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_restart_pending_shadow_does_not_write_and_failed_unload_keeps_services(
    hass, hass_storage
):
    from dataclasses import asdict

    from custom_components.ecoflow_smart_charge.storage import SessionRecord

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "reserve_entities": [f"number.reserve_{i}" for i in range(3)],
            "legacy_writer_entities": ["automation.legacy"],
            "journal_initialized": True,
        },
        options={"mode": "active"},
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
    hass.states.async_set("automation.legacy", "off")
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
    await hass.services.async_call(
        DOMAIN,
        "confirm_recovery",
        {"config_entry_id": entry.entry_id, "confirmed": True},
        blocking=True,
    )
    assert len(calls) == 3 and runtime.mode == "shadow"
    for e, v in originals.items():
        hass.states.async_set(e, str(v), {"unit_of_measurement": "%"})
    await hass.services.async_call(
        DOMAIN,
        "confirm_recovery",
        {"config_entry_id": entry.entry_id, "confirmed": True},
        blocking=True,
    )
    assert runtime.journal.record is None
    from homeassistant.config_entries import ConfigEntryState

    assert entry.state is ConfigEntryState.FAILED_UNLOAD
    # HA marks failed unload nonrecoverable; after explicit recovery a restart is
    # required. Exercise component cleanup directly, not a fabricated manager state.
    from custom_components.ecoflow_smart_charge import async_unload_entry

    assert await async_unload_entry(hass, entry)
