"""Retained PV probes recover after missed days without duplicate learning."""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from test_executor import Disk

from custom_components.ecoflow_smart_charge.reader import SourceReader
from custom_components.ecoflow_smart_charge.storage import PersistentSessionStore


@pytest.mark.parametrize(
    ("probe_day", "now_utc", "hours"),
    [
        ("2026-01-03", "2026-01-05T14:00:00+00:00", 24),
        ("2026-03-29", "2026-03-31T14:00:00+00:00", 23),
        ("2026-10-25", "2026-10-27T14:00:00+00:00", 25),
    ],
)
@pytest.mark.parametrize("initially_complete", [True, False])
async def test_overdue_probe_recovers_correct_local_day_after_restart(
    hass, freezer, probe_day, now_utc, hours, initially_complete
):
    freezer.move_to(now_utc)
    zone = ZoneInfo("Europe/Berlin")
    now = datetime.fromisoformat(now_utc).astimezone(zone)
    disk = Disk()
    journal = PersistentSessionStore(disk)
    original = {
        "probe_day": probe_day,
        "probe_kwh": 5.0,
        "ratios": [1, 1, 1],
        "correction": 1.0,
        "learned_day": None,
    }
    await journal.async_set_learning(original)
    # Simulate HA restarting after the entire following-day evaluation window.
    journal = PersistentSessionStore(disk)
    await journal.async_load()
    entry = MockConfigEntry(
        domain="ecoflow_smart_charge",
        data={"pv_entity": "sensor.pv", "forecast_today_entity": "sensor.forecast"},
    )
    hass.states.async_set("sensor.forecast", "8", {"unit_of_measurement": "kWh"})
    reader = SourceReader(hass, entry, journal)
    start = datetime.fromisoformat(probe_day).replace(tzinfo=zone)
    end = start + timedelta(days=1)
    assert (end.astimezone(UTC) - start.astimezone(UTC)).total_seconds() / 3600 == hours

    with (
        patch("custom_components.ecoflow_smart_charge.reader.dt_util.now", return_value=now),
        patch(
            "custom_components.ecoflow_smart_charge.reader.read_daily_pv",
            return_value=(6.0, hours if initially_complete else 12),
        ) as daily,
    ):
        await reader.learn()
    daily.assert_awaited_once_with(hass, "sensor.pv", start, end)
    if not initially_complete:
        assert journal.learning == original  # do not overwrite or fabricate evidence
        now += timedelta(days=1)
        freezer.move_to(now)
        hass.states.async_set("sensor.forecast", "8", {"unit_of_measurement": "kWh"})
        with (
            patch("custom_components.ecoflow_smart_charge.reader.dt_util.now", return_value=now),
            patch(
                "custom_components.ecoflow_smart_charge.reader.read_daily_pv",
                return_value=(6.0, hours),
            ) as retry,
        ):
            await reader.learn()
        retry.assert_awaited_once_with(hass, "sensor.pv", start, end)
    assert journal.learning["learned_day"] == probe_day
    assert journal.learning["ratios"] == [1, 1, 1, 1.2]
    assert journal.learning["probe_day"] == now.date().isoformat()
    assert journal.learning["probe_kwh"] == 8.0

    # A second restart must not learn the old day twice or query today's incomplete day.
    saved = dict(journal.learning)
    restarted = PersistentSessionStore(disk)
    await restarted.async_load()
    with (
        patch("custom_components.ecoflow_smart_charge.reader.dt_util.now", return_value=now),
        patch("custom_components.ecoflow_smart_charge.reader.read_daily_pv") as daily,
    ):
        await SourceReader(hass, entry, restarted).learn()
    daily.assert_not_awaited()
    assert restarted.learning == saved


async def test_probe_day_that_never_completes_is_closed_after_a_week(hass, freezer):
    freezer.move_to("2026-01-12T14:00:00+00:00")
    now = datetime.fromisoformat("2026-01-12T14:00:00+00:00")
    journal = PersistentSessionStore(Disk())
    # E.g. installed in the afternoon: the own PV sensor has only part of the first day.
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
    with (
        patch("custom_components.ecoflow_smart_charge.reader.dt_util.now", return_value=now),
        patch(
            "custom_components.ecoflow_smart_charge.reader.read_daily_pv",
            return_value=(2.0, 10),
        ),
    ):
        await SourceReader(hass, entry, journal).learn()
    assert journal.learning["learned_day"] == "2026-01-03"
    assert journal.learning["ratios"] == [1, 1, 1]
    assert journal.learning["probe_day"] == "2026-01-12"
