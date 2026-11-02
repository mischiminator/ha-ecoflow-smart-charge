"""Fail-closed inputs and actual published quarter-hour series boundaries."""

from dataclasses import replace
from datetime import timedelta

import pytest
from test_economics import candidate

from custom_components.ecoflow_smart_charge.planner.core import (
    PRICE_MAX_AGE,
    Battery,
    PricePoint,
    decide,
)


# A quarter-hourly price is still valid right at the next boundary (900 s).
@pytest.mark.parametrize(
    "age,allowed",
    [
        (-0.001, False),
        (0, True),
        (900, True),
        (PRICE_MAX_AGE - 0.001, True),
        (PRICE_MAX_AGE, False),
    ],
)
def test_price_source_age_exclusive(age, allowed):
    c = candidate()
    assert (
        decide(replace(c, price_series_updated=c.now - timedelta(seconds=age))).allowed is allowed
    )


@pytest.mark.parametrize(
    "field,bad",
    [
        ("current_price_ct", None),
        ("below_horizon", None),
        ("current_price_ct", float("nan")),
        ("efficiency", True),
        ("forecast_today", float("inf")),
        ("forecast_tomorrow", -1),
        ("pv_correction", -1),
        ("wear_cost_ct", True),
        ("minimum_net_saving_ct", float("nan")),
        ("charge_ceiling_ct", float("nan")),
        ("batteries", (Battery(50, 2),) * 3),
        ("batteries", (Battery(True, 3),) * 3),
        ("batteries", ()),
        ("batteries", (Battery(50, 3),) * 11),
        ("sources_fresh", None),
        ("protection_mode", None),
        ("best_price_window", "on"),
        ("active_session", "off"),
        ("full_marker_for_solar_day", None),
    ],
)
def test_invalid_required_inputs_fail_closed(field, bad):
    assert not decide(candidate(**{field: bad})).allowed


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


def test_nonfinite_derived_projection_is_rejected():
    c = candidate(capacity_kwh=1e308, minimum_net_saving_ct=0)
    assert not decide(c).allowed
    c = candidate(forecast_today=1e308, pv_correction=1e308, active_session=True)
    assert not decide(c).allowed


def test_naive_and_past_sunset_do_not_raise_or_allow():
    c = candidate()
    for changed in (
        {"now": c.now.replace(tzinfo=None)},
        {"sunset": c.now},
        {"sunset": c.sunset.replace(tzinfo=None)},
        {"price_series_updated": c.now.replace(tzinfo=None)},
    ):
        assert not decide(replace(c, **changed)).allowed
