"""Recorder plausibility, calendar and alias-free row counting regression."""

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import pytest
from test_profile import rows

from custom_components.ecoflow_smart_charge.planner.core import build_hourly_profile


@pytest.mark.parametrize(
    "load,pv,valid",
    [
        (0, 0, True),
        (10, 10, True),
        (-0.000001, 0, False),
        (10.000001, 0, False),
        (1, -0.000001, False),
        (1, 10.000001, False),
    ],
)
def test_inclusive_zero_ten_plausibility_caps(load, pv, valid):
    now = datetime(2026, 1, 4, tzinfo=UTC)
    data = [
        dict(r, grid=load - pv, pv=pv, charges=(0, 0, 0), discharges=(0, 0, 0))
        for r in rows(now, 3)
    ]
    assert build_hourly_profile(data, now=now).valid is valid


def test_duplicate_instants_and_naive_rows_cannot_fake_history():
    now = datetime(2026, 1, 4, tzinfo=UTC)
    data = list(rows(now, 2))
    assert not build_hourly_profile(data + data + data, now=now).valid
    naive = [dict(r, start=r["start"].replace(tzinfo=None)) for r in rows(now, 3)]
    assert not build_hourly_profile(naive, now=now).valid
    assert not build_hourly_profile(data, now=now.replace(tzinfo=None)).valid


def test_spring_hour_is_absent_not_fabricated():
    now = datetime(2026, 4, 2, 10, tzinfo=ZoneInfo("Europe/Berlin"))
    p = build_hourly_profile(rows(now), now=now)
    assert p.valid
    assert p.samples_by_hour[2] == 13
    assert p.samples_by_hour[3] == 14
    assert sum(p.samples_by_hour) == 14 * 24 - 1
