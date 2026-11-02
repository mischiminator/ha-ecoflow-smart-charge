"""Config flow validation must reject incomplete three-battery controller mappings."""

from __future__ import annotations

import pytest

from custom_components.ecoflow_smart_charge.const import DOMAIN


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_config_flow_rejects_incomplete_three_battery_mapping(hass) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    assert result["type"] == "form"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "name": "Test controller",
            "forecast_today_entity": "sensor.forecast_today",
            "forecast_remaining_entity": "sensor.forecast_remaining",
            "forecast_tomorrow_entity": "sensor.forecast_tomorrow",
            "sun_entity": "sun.test",
            "tariff_key": "Synthetic",
            "charge_energy_entities": ["sensor.charge_1", "sensor.charge_2", "sensor.charge_3"],
            "discharge_energy_entities": [
                "sensor.discharge_1",
                "sensor.discharge_2",
                "sensor.discharge_3",
            ],
            "grid_energy_entity": "sensor.grid",
            "price_entity": "sensor.price",
            "price_window_entity": "binary_sensor.window",
            "pv_entity": "sensor.pv",
            "soc_entities": ["sensor.soc_1", "sensor.soc_2"],
            "reserve_entities": ["number.reserve_1", "number.reserve_2", "number.reserve_3"],
            "self_powered_entities": ["switch.self_1", "switch.self_2", "switch.self_3"],
            "operating_mode_entities": ["select.mode_1", "select.mode_2", "select.mode_3"],
        },
    )
    assert result["type"] == "form"
    assert result["errors"]["base"] == "three_batteries_required"
