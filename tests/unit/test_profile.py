"""Synthetic energy rows, not household traces."""

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from custom_components.ecoflow_smart_charge.planner.core import build_hourly_profile


def rows(now, days=14):
    end = now.replace(hour=0, minute=0, second=0, microsecond=0)
    start = (end - timedelta(days=days)).astimezone(UTC)
    while start < end.astimezone(UTC):
        yield {
            "start": start,
            "grid": -0.2,
            "pv": 1.0,
            "charges": (0.1, 0.2, 0.3),
            "discharges": (0.2, 0.3, 0.4),
        }
        start += timedelta(hours=1)


def test_completed_local_days_signed_grid_and_dst():
    now = datetime(2026, 11, 2, 10, tzinfo=ZoneInfo("Europe/Berlin"))
    data = list(rows(now))
    data.append(dict(data[0], start=now.replace(hour=0), grid=9))
    data.append(dict(data[0], start=now - timedelta(days=15), grid=9))
    p = build_hourly_profile(data, now=now)
    assert p.valid
    assert p.samples_by_hour[2] == 15
    assert p.samples_by_hour[0] == 14
    assert p.house_by_hour == pytest.approx((1.1,) * 24)


@pytest.mark.parametrize(
    "field,bad",
    [
        ("grid", True),
        ("pv", float("nan")),
        ("grid", float("inf")),
        ("charges", (0, 0)),
        ("charges", (-1, 0, 0)),
        ("discharges", (True, 0, 0)),
    ],
)
def test_invalid_rows_cannot_satisfy_three_sample_minimum(field, bad):
    now = datetime(2026, 1, 4, 10, tzinfo=UTC)
    data = list(rows(now, 3))
    data[0][field] = bad
    assert not build_hourly_profile(data, now=now).valid
