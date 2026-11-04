"""Fail-closed inputs and actual published quarter-hour series boundaries."""

from dataclasses import replace
from datetime import timedelta

import pytest
from test_economics import candidate

from custom_components.ecoflow_smart_charge.planner.core import (
    Battery,
    PricePoint,
    decide,
)


@pytest.mark.parametrize("difference,allowed", [(0.050999, True), (0.051, False), (-0.051, False)])
def test_current_quote_strict_tolerance(difference, allowed):
    c = candidate(current_price_ct=difference)
    c = replace(c, prices=(PricePoint(c.now, 0),) + c.prices[1:])
    assert decide(c).allowed is allowed


def test_duplicate_unsorted_and_hourly_series_are_rejected():
    c = candidate()
    for series in (c.prices + (c.prices[-1],), c.prices[::-1], c.prices[::4]):
        assert not decide(replace(c, prices=series)).allowed


def test_untraversed_gap_does_not_invalidate_fully_covered_target():
    c = candidate()
    # tiny target is covered at 12:15; the gap after 12:30 is irrelevant.
    c = replace(c, batteries=(Battery(99, 99),) * 3, prices=c.prices[:3] + c.prices[4:])
    assert decide(c).allowed


def test_off_quarter_time_and_missing_current_slot():
    c = candidate()
    assert decide(replace(c, now=c.now + timedelta(minutes=7))).allowed
    assert not decide(replace(c, prices=c.prices[1:])).allowed


def test_past_sunset_does_not_allow():
    c = candidate()
    assert not decide(replace(c, sunset=c.now)).allowed
