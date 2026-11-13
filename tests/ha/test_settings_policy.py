"""Settings policies preserve advanced values and share one effective backend model."""

import pytest
from test_config_flow import submit
from test_native import selection

from custom_components.ecoflow_smart_charge.const import DOMAIN


def test_effective_policy_and_legacy_preservation():
    from custom_components.ecoflow_smart_charge.settings import effective_settings, merge_settings

    legacy = {"minimum_net_saving_ct": 8.7, "minimum_price_advantage_percent": 27.5}
    assert effective_settings(legacy)["settings_mode"] == "advanced"
    assert effective_settings(legacy)["minimum_net_saving_ct"] == 8.7
    for policy, threshold in (("save_more", 1), ("balanced", 3), ("protect_battery", 6)):
        simple = merge_settings(legacy, {"settings_mode": "simple", "charging_policy": policy})
        effective = effective_settings(simple)
        assert effective["minimum_net_saving_ct"] == threshold
        assert effective["minimum_price_advantage_percent"] == 0
        assert simple["minimum_net_saving_ct"] == 8.7
        assert (
            effective_settings(merge_settings(simple, {"settings_mode": "advanced"}))[
                "minimum_price_advantage_percent"
            ]
            == 27.5
        )
        edited = merge_settings(simple, {"minimum_net_saving_ct": 9.2})
        assert edited["settings_mode"] == "advanced"
        assert effective_settings(edited)["minimum_net_saving_ct"] == 9.2


@pytest.mark.parametrize(
    "key,value",
    [
        ("settings_mode", []),
        ("settings_mode", "active"),
        ("charging_policy", {}),
        ("charging_policy", "cheap"),
    ],
)
def test_reject_malformed_policy(key, value):
    from custom_components.ecoflow_smart_charge.config_flow import validate_settings

    with pytest.raises(ValueError):
        validate_settings({key: value})


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_options_and_number_roundtrips(hass):
    result = await submit(hass, selection(hass))
    entry = result["result"]
    await hass.async_block_till_done()
    assert entry.options["settings_mode"] == "simple"
    assert entry.options["charging_policy"] == "balanced"
    runtime = entry.runtime_data
    from custom_components.ecoflow_smart_charge.number import SettingNumber

    await SettingNumber(entry, "minimum_net_saving_ct").async_set_native_value(8.7)
    assert entry.options["settings_mode"] == "advanced"
    await runtime.async_set_setting("minimum_price_advantage_percent", 27.5)
    await runtime.async_set_setting("charge_ceiling_ct", 29.3)
    await runtime.async_set_setting("efficiency", 0.79)
    await runtime.async_set_setting("wear_cost_ct", 4.6)
    await runtime.async_set_setting("capacity_kwh", 3.21)
    await runtime.async_set_setting("charging_policy", "protect_battery")
    for mode in ("simple", "advanced"):
        flow = await hass.config_entries.options.async_init(entry.entry_id)
        assert "minimum_net_saving_ct" not in {str(k) for k in flow["data_schema"].schema}
        form = await hass.config_entries.options.async_configure(
            flow["flow_id"], {"settings_mode": mode}
        )
        fields = {str(k) for k in form["data_schema"].schema}
        assert ("minimum_net_saving_ct" in fields) == (mode == "advanced")
        assert ("charging_policy" in fields) == (mode == "simple")
        if mode == "simple":
            assert fields == {"master", "mode", "charging_policy"}
        saved = await hass.config_entries.options.async_configure(form["flow_id"], {})
        assert saved["type"] == "create_entry"
        await hass.async_block_till_done()
        assert entry.options["minimum_net_saving_ct"] == 8.7
        assert entry.options["minimum_price_advantage_percent"] == 27.5
        assert entry.options["settings_mode"] == mode
        assert entry.options["charge_ceiling_ct"] == 29.3
        assert entry.options["efficiency"] == 0.79
        assert entry.options["wear_cost_ct"] == 4.6
        assert entry.options["capacity_kwh"] == 3.21
        assert entry.runtime_data is runtime
        assert runtime.applied_options == dict(entry.options)
        assert entry.options["charging_policy"] == "protect_battery"
    assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.parametrize(
    "policy,threshold,allowed",
    [("save_more", 1.0, True), ("balanced", 3.0, True), ("protect_battery", 6.0, False)],
)
async def test_reader_and_planner_use_effective_policy(hass, freezer, policy, threshold, allowed):
    from datetime import UTC, datetime, timedelta
    from unittest.mock import patch

    from homeassistant.core import SupportsResponse
    from pytest_homeassistant_custom_component.common import MockConfigEntry
    from test_source_pipeline import data_states

    from custom_components.ecoflow_smart_charge.reader import SourceReader
    from custom_components.ecoflow_smart_charge.storage import PersistentSessionStore

    freezer.move_to("2026-01-04T20:00:00+00:00")
    now = datetime.now(UTC)
    data = data_states(hass, now)
    options = {
        "settings_mode": "simple",
        "charging_policy": policy,
        "minimum_net_saving_ct": 999,
        "minimum_price_advantage_percent": 99,
        "master": True,
        "efficiency": 0.8,
        "wear_cost_ct": 2,
    }
    entry = MockConfigEntry(domain=DOMAIN, data=data, options=options)
    reader = SourceReader(hass, entry, PersistentSessionStore(None))
    rows = [
        {
            "start": (now - timedelta(days=d)).replace(hour=h),
            "grid": 2.0,
            "pv": 0.0,
            "charges": (0.0,) * 3,
            "discharges": (0.0,) * 3,
        }
        for d in range(1, 15)
        for h in range(24)
    ]

    async def prices(call):
        return {
            "prices": {
                "Chosen": [
                    {
                        "start_time": (now + timedelta(minutes=15 * i)).isoformat(),
                        "price": 0.10 if i == 0 else 0.19,
                    }
                    for i in range(192)
                ]
            }
        }

    hass.services.async_register(
        "tibber", "get_prices", prices, supports_response=SupportsResponse.ONLY
    )
    with patch("custom_components.ecoflow_smart_charge.reader.read_statistics", return_value=rows):
        gate = await reader.refresh()
    assert gate["valid"]
    assert gate["allowed"] is allowed
    assert reader.input.minimum_net_saving_ct == threshold
    assert reader.input.minimum_price_advantage_percent == 0
    assert reader.last_plan.net_saving_ct == pytest.approx(4.5)
    assert entry.options["minimum_net_saving_ct"] == 999


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_legacy_native_options_and_selects(hass):
    from homeassistant.data_entry_flow import InvalidData
    from pytest_homeassistant_custom_component.common import MockConfigEntry
    from test_native import mapping

    from custom_components.ecoflow_smart_charge.const import DOMAIN
    from custom_components.ecoflow_smart_charge.select import SettingsSelect
    from custom_components.ecoflow_smart_charge.settings import (
        CHARGING_POLICIES,
        SETTINGS_MODES,
        effective_settings,
    )

    entry = MockConfigEntry(
        domain=DOMAIN,
        data=mapping(hass),
        options={
            "minimum_net_saving_ct": 8.7,
            "minimum_price_advantage_percent": 27.5,
            "charge_ceiling_ct": 28.3,
            "master": False,
            "mode": "shadow",
            "unrelated": "keep",
        },
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    mode = SettingsSelect(entry, "settings_mode", SETTINGS_MODES)
    policy = SettingsSelect(entry, "charging_policy", CHARGING_POLICIES)
    assert mode.current_option == "advanced"
    assert effective_settings(entry.options)["minimum_net_saving_ct"] == 8.7
    before = dict(entry.options)
    for entity, invalid in ((mode, "active"), (policy, "invalid")):
        with pytest.raises(ValueError):
            await entity.async_select_option(invalid)
        assert dict(entry.options) == before
    await mode.async_select_option("simple")
    await policy.async_select_option("save_more")
    assert effective_settings(entry.options)["minimum_net_saving_ct"] == 1
    assert entry.options["mode"] == "shadow" and entry.options["master"] is False
    flow = await hass.config_entries.options.async_init(entry.entry_id)
    with pytest.raises(InvalidData):
        await hass.config_entries.options.async_configure(
            flow["flow_id"], {"settings_mode": "active"}
        )
    flow = await hass.config_entries.options.async_init(entry.entry_id)
    form = await hass.config_entries.options.async_configure(
        flow["flow_id"], {"settings_mode": "advanced"}
    )
    saved = await hass.config_entries.options.async_configure(form["flow_id"], {})
    assert saved["type"] == "create_entry"
    await hass.async_block_till_done()
    assert entry.options["unrelated"] == "keep"
    assert entry.options["minimum_net_saving_ct"] == 8.7
    assert entry.options["minimum_price_advantage_percent"] == 27.5
    assert entry.options["charge_ceiling_ct"] == 28.3
    assert await hass.config_entries.async_unload(entry.entry_id)
