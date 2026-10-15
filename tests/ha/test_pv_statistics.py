"""PV learning depends on measured PV, not grid or battery statistics availability."""

from datetime import UTC, datetime, timedelta

from homeassistant.components.recorder.models import StatisticMeanType
from homeassistant.components.recorder.statistics import async_import_statistics


async def test_pv_learning_query_uses_only_selected_pv_and_normalizes_wh(recorder_mock, hass):
    from custom_components.ecoflow_smart_charge.reader import read_daily_pv

    start = datetime(2026, 1, 3, tzinfo=UTC)
    async_import_statistics(
        hass,
        {
            "statistic_id": "sensor.synthetic_pv",
            "source": "recorder",
            "name": None,
            "unit_of_measurement": "Wh",
            "unit_class": "energy",
            "has_sum": True,
            "mean_type": StatisticMeanType.NONE,
        },
        [
            {"start": start + timedelta(hours=i), "sum": 250.0 * i, "state": 250.0 * i}
            for i in range(25)
        ],
    )
    # HA first schedules the import task onto Recorder's queue.
    await hass.async_block_till_done()
    from pytest_homeassistant_custom_component.components.recorder.common import (
        async_wait_recording_done,
    )

    await async_wait_recording_done(hass)
    from functools import partial

    from homeassistant.components.recorder.statistics import get_metadata

    metadata = await recorder_mock.async_add_executor_job(
        partial(get_metadata, hass, statistic_ids={"sensor.synthetic_pv"})
    )
    assert "sensor.synthetic_pv" in metadata, metadata
    energy, count = await read_daily_pv(
        hass, "sensor.synthetic_pv", start + timedelta(hours=1), start + timedelta(days=1)
    )
    assert count == 23 and energy == 5.75
