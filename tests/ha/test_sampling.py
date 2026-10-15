"""Sampling uses installation-local time, independently of other source history."""

from unittest.mock import patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ecoflow_smart_charge.reader import SourceReader
from custom_components.ecoflow_smart_charge.storage import PersistentSessionStore


class Disk:
    async def async_save(self, data):
        self.data = data


@pytest.mark.parametrize("value,unit", [("6", "kWh"), ("6000", "Wh")])
async def test_new_daily_probe_is_captured_without_recorder_yesterday(hass, freezer, value, unit):
    freezer.move_to("2026-01-04T14:00:00+00:00")  # after 05:00 in HA's test zone
    journal = PersistentSessionStore(Disk())
    entry = MockConfigEntry(
        domain="ecoflow_smart_charge",
        data={
            "forecast_today_entity": "sensor.synthetic_forecast",
            "pv_entity": "sensor.synthetic_pv",
        },
    )
    hass.states.async_set("sensor.synthetic_forecast", value, {"unit_of_measurement": unit})
    reader = SourceReader(hass, entry, journal)
    with patch(
        "custom_components.ecoflow_smart_charge.reader.read_daily_pv",
        side_effect=KeyError("history not ready"),
    ) as daily:
        await reader.learn()
    daily.assert_not_called()
    assert journal.learning["probe_kwh"] == 6
    assert journal.learning["probe_day"] == "2026-01-04"


async def test_failed_forecast_does_not_lose_successfully_evaluated_prior_probe(hass, freezer):
    freezer.move_to("2026-01-04T14:00:00+00:00")
    journal = PersistentSessionStore(Disk())
    yesterday = "2026-01-03"
    await journal.async_set_learning(
        {
            "probe_day": yesterday,
            "probe_kwh": 5.0,
            "ratios": [1, 1, 1],
            "correction": 1.0,
            "learned_day": None,
        }
    )
    entry = MockConfigEntry(
        domain="ecoflow_smart_charge",
        data={"pv_entity": "sensor.pv", "forecast_today_entity": "sensor.missing"},
    )
    reader = SourceReader(hass, entry, journal)
    with patch(
        "custom_components.ecoflow_smart_charge.reader.read_daily_pv", return_value=(6.0, 24)
    ):
        await reader.learn()
    assert journal.learning["learned_day"] == yesterday
    assert journal.learning["ratios"][-1] == 1.2


async def test_incomplete_pv_day_does_not_finalize_or_replace_pending_probe(hass, freezer):
    freezer.move_to("2026-01-04T14:00:00+00:00")
    journal = PersistentSessionStore(Disk())
    await journal.async_set_learning(
        {
            "probe_day": "2026-01-03",
            "probe_kwh": 5.0,
            "ratios": [1, 1, 1],
            "correction": 1.0,
            "learned_day": None,
        }
    )
    entry = MockConfigEntry(
        domain="ecoflow_smart_charge",
        data={"pv_entity": "sensor.pv", "forecast_today_entity": "sensor.forecast"},
    )
    hass.states.async_set("sensor.forecast", "8", {"unit_of_measurement": "kWh"})
    reader = SourceReader(hass, entry, journal)
    with patch(
        "custom_components.ecoflow_smart_charge.reader.read_daily_pv", return_value=(2.0, 12)
    ):
        await reader.learn()
    assert journal.learning["learned_day"] is None
    assert journal.learning["probe_day"] == "2026-01-03"
    assert journal.learning["probe_kwh"] == 5.0
