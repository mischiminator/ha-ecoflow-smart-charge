"""Read-only source boundary, using synthetic data only."""

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from homeassistant.core import State


async def test_reader_parses_only_selected_published_tariff():
    from custom_components.ecoflow_smart_charge.reader import parse_prices

    data = {
        "prices": {
            "Other": [{"start_time": "2026-01-04T12:00:00+00:00", "price": 9}],
            "Selected": [{"start_time": "2026-01-04T12:00:00+00:00", "price": 0.12}],
        }
    }
    assert parse_prices(data, "Selected")[0].price_ct == 12
    with pytest.raises(ValueError):
        parse_prices(data, "Missing")


@pytest.mark.parametrize("seconds,expected", [(599, True), (600, False), (-1, False)])
async def test_source_freshness_exclusive_and_future(seconds, expected):
    from custom_components.ecoflow_smart_charge.reader import fresh

    now = datetime.now(UTC)
    state = State(
        "sensor.soc",
        "55",
        last_updated=now - timedelta(seconds=seconds),
        last_reported=now - timedelta(seconds=seconds),
    )
    assert fresh(state, now, 600) is expected


async def test_join_has_no_missing_stream_zero_fallback():
    from custom_components.ecoflow_smart_charge.reader import join_statistics

    keys = [f"sensor.stream_{i}" for i in range(8)]
    raw = {k: [{"start": 1767528000.0, "change": 1.0}] for k in keys}
    rows = join_statistics(raw, keys, ZoneInfo("Europe/Berlin"))
    assert len(rows) == 1 and rows[0]["charges"] == (1, 1, 1)
    raw[keys[-1]] = []
    assert join_statistics(raw, keys, ZoneInfo("Europe/Berlin")) == []


async def test_recorder_query_real_populated_sqlite(recorder_mock, hass):
    from homeassistant.components.recorder.models import StatisticMeanType
    from homeassistant.components.recorder.statistics import async_import_statistics

    from custom_components.ecoflow_smart_charge.reader import read_statistics

    start = datetime(2026, 1, 3, tzinfo=UTC)
    keys = [f"sensor.synthetic_{i}" for i in range(8)]
    for key in keys:
        async_import_statistics(
            hass,
            {
                "statistic_id": key,
                "source": "recorder",
                "name": None,
                "unit_of_measurement": "Wh",
                "unit_class": "energy",
                "has_sum": True,
                "mean_type": StatisticMeanType.NONE,
            },
            [
                {"start": start + timedelta(hours=i), "sum": 1000.0 * i, "state": 1000.0 * i}
                for i in range(5)
            ],
        )
    from pytest_homeassistant_custom_component.components.recorder.common import (
        async_wait_recording_done,
    )

    await async_wait_recording_done(hass)
    rows = await read_statistics(
        hass, keys, start + timedelta(hours=1), start + timedelta(hours=5), ZoneInfo("UTC")
    )
    assert len(rows) == 4
    assert all(row["grid"] == 1.0 for row in rows)


async def test_join_splits_any_battery_count():
    from custom_components.ecoflow_smart_charge.reader import join_statistics

    for batteries in (1, 4):
        keys = [f"sensor.stream_{i}" for i in range(2 + 2 * batteries)]
        raw = {k: [{"start": 1767528000.0, "change": float(i)}] for i, k in enumerate(keys)}
        row = join_statistics(raw, keys, ZoneInfo("Europe/Berlin"))[0]
        assert row["charges"] == tuple(float(i) for i in range(2, 2 + batteries))
        assert row["discharges"] == tuple(float(i) for i in range(2 + batteries, len(keys)))
    for keys in (["sensor.grid", "sensor.pv"], ["sensor.grid", "sensor.pv", "sensor.charge"]):
        with pytest.raises(ValueError):
            join_statistics({}, keys, ZoneInfo("Europe/Berlin"))
