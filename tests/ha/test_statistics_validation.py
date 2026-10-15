"""Recorder metadata is authoritative for units; never assume native sums are kWh."""

from datetime import UTC, datetime, timedelta

import pytest
from homeassistant.components.recorder.models import StatisticMeanType
from homeassistant.components.recorder.statistics import async_import_statistics


async def test_recorder_unknown_unit_cannot_be_used_as_kwh(recorder_mock, hass):
    from custom_components.ecoflow_smart_charge.reader import read_statistics

    start = datetime(2026, 1, 3, tzinfo=UTC)
    keys = [f"sensor.unknown_unit_{i}" for i in range(8)]
    for key in keys:
        async_import_statistics(
            hass,
            {
                "statistic_id": key,
                "source": "recorder",
                "name": None,
                "unit_of_measurement": None,
                "unit_class": None,
                "has_sum": True,
                "mean_type": StatisticMeanType.NONE,
            },
            [
                {"start": start + timedelta(hours=i), "sum": float(i), "state": float(i)}
                for i in range(3)
            ],
        )
    from pytest_homeassistant_custom_component.components.recorder.common import (
        async_wait_recording_done,
    )

    await async_wait_recording_done(hass)
    with pytest.raises(ValueError):
        await read_statistics(hass, keys, start, start + timedelta(hours=3), UTC)


async def test_duplicate_history_row_is_invalid_not_first_wins():
    from custom_components.ecoflow_smart_charge.reader import join_statistics

    keys = [f"sensor.stream_{i}" for i in range(8)]
    raw = {k: [{"start": 1767528000.0, "change": 1.0}] for k in keys}
    raw[keys[0]].append({"start": 1767528000.0, "change": 2.0})
    assert join_statistics(raw, keys, UTC) == []
