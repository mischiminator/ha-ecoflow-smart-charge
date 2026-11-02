"""HA-free planning primitives; no Home Assistant or I/O imports are permitted."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from math import ceil, floor, sqrt

from .forecast import build_curve
from .learning import correction_from_ratios, learn_pv_correction
from .validation import aware, number

__all__ = [
    "MAX_BATTERIES",
    "PRICE_MAX_AGE",
    "Battery",
    "HourlyProfile",
    "PlanResult",
    "PlannerInput",
    "PricePoint",
    "build_hourly_profile",
    "correction_from_ratios",
    "decide",
    "learn_pv_correction",
]

EPSILON = 1e-9
# The current price is reported once per quarter hour; a little slack keeps the minute
# safety check from seeing it stale right at the boundary.
PRICE_MAX_AGE = 1200
# Any 1..MAX_BATTERIES batteries; the bound only rejects corrupt mappings.
MAX_BATTERIES = 10


@dataclass(frozen=True)
class Battery:
    soc: float
    reserve: float
    # Model capacity; None falls back to PlannerInput.capacity_kwh.
    capacity_kwh: float | None = None


@dataclass(frozen=True)
class PricePoint:
    starts_at: datetime
    price_ct: float


@dataclass(frozen=True)
class HourlyProfile:
    house_by_hour: tuple[float, ...]
    pv_by_hour: tuple[float, ...]
    samples_by_hour: tuple[int, ...]
    valid: bool
    reason: str


@dataclass(frozen=True)
class PlannerInput:
    now: datetime
    prices: tuple[PricePoint, ...]
    price_series_updated: datetime
    best_price_window: bool
    profile: HourlyProfile
    forecast_today: float
    forecast_tomorrow: float
    pv_correction: float
    sunset: datetime
    batteries: tuple[Battery, ...]
    capacity_kwh: float
    efficiency: float
    wear_cost_ct: float
    charge_ceiling_ct: float
    minimum_net_saving_ct: float
    minimum_price_advantage_percent: float
    active_session: bool
    full_marker_for_solar_day: bool
    sources_fresh: bool
    protection_mode: bool
    current_price_ct: float | None = None
    below_horizon: bool | None = None


@dataclass(frozen=True)
class PlanResult:
    allowed: bool
    reason: str
    missing_energy_kwh: float
    solar_surplus_kwh: float
    avoided_price_ct: float
    net_saving_ct: float
    price_advantage_percent: float | None
    command_plan: tuple[str, ...] = ()
    solar_day: str | None = None
    coverage_kwh: float = 0.0
    target_ac_kwh: float = 0.0
    coverage_fraction: float = 0.0
    cost_ct: float = 0.0
    grid_kwh: float = 0.0
    # One reserve for all batteries (the devices sync it): grid fills up to here, PV the rest.
    target_soc: float | None = None


def build_hourly_profile(
    rows: Iterable[dict[str, object]], *, now: datetime | None = None
) -> HourlyProfile:
    """Average complete local days; repeated DST hours are distinct UTC samples."""
    buckets: list[list[tuple[float, float]]] = [[] for _ in range(24)]
    if now is not None and not aware(now):
        return HourlyProfile((0.0,) * 24, (0.0,) * 24, (0,) * 24, False, "time_invalid")
    end = now.replace(hour=0, minute=0, second=0, microsecond=0) if now else None
    begin = end - timedelta(days=14) if end else None
    seen: set[datetime] = set()
    for row in rows:
        try:
            stamp = row["start"]
            if not aware(stamp):
                continue
            instant = stamp.astimezone(UTC)
            if instant in seen:
                continue
            seen.add(instant)
            if end and not begin.astimezone(UTC) <= instant < end.astimezone(UTC):
                continue
            grid, pv = row["grid"], row["pv"]
            charges, discharges = tuple(row["charges"]), tuple(row["discharges"])
            if not 1 <= len(charges) == len(discharges) <= MAX_BATTERIES:
                continue
            if not all(number(v) for v in (grid, pv, *charges, *discharges)):
                continue
            if any(v < 0 for v in (*charges, *discharges)):
                continue
        except KeyError, TypeError, ValueError:
            continue
        load = grid + pv - sum(charges) + sum(discharges)
        if not 0 <= load <= 10 or not 0 <= pv <= 10:
            continue
        hour = stamp.astimezone(now.tzinfo).hour if now else stamp.hour
        buckets[hour].append((load, pv))
    counts = tuple(len(bucket) for bucket in buckets)
    valid = min(counts, default=0) >= 3
    return HourlyProfile(
        house_by_hour=tuple(sum(v[0] for v in b) / len(b) if b else 0.0 for b in buckets),
        pv_by_hour=tuple(sum(v[1] for v in b) / len(b) if b else 0.0 for b in buckets),
        samples_by_hour=counts,
        valid=valid,
        reason="ok" if valid else "insufficient_hourly_samples",
    )


def _reason(value: PlannerInput) -> str | None:
    if not all(aware(t) for t in (value.now, value.price_series_updated, value.sunset)):
        return "time_invalid"
    if value.sunset.timestamp() <= value.now.timestamp():
        return "sunset_invalid"
    if not 0 <= value.now.timestamp() - value.price_series_updated.timestamp() < PRICE_MAX_AGE:
        return "prices_stale"
    flags = (
        value.best_price_window,
        value.active_session,
        value.full_marker_for_solar_day,
        value.sources_fresh,
        value.protection_mode,
        value.below_horizon,
    )
    if any(type(f) is not bool for f in flags):
        return "required_state_invalid"
    if not value.sources_fresh:
        return "sources_stale"
    if not value.protection_mode:
        return "protection_mode_required"
    p = value.profile
    if (
        p.valid is not True
        or any(len(v) != 24 for v in (p.house_by_hour, p.pv_by_hour, p.samples_by_hour))
        or any(not number(v) or not 0 <= v <= 10 for v in (*p.house_by_hour, *p.pv_by_hour))
        or any(type(n) is not int or n < 3 for n in p.samples_by_hour)
    ):
        return "profile_invalid"
    if not 1 <= len(value.batteries) <= MAX_BATTERIES or any(
        not number(b.soc)
        or not number(b.reserve)
        or not 0 <= b.soc <= 100
        or not 3 <= b.reserve <= 100
        or (b.capacity_kwh is not None and (not number(b.capacity_kwh) or b.capacity_kwh <= 0))
        for b in value.batteries
    ):
        return "battery_data_invalid"
    parameters = (
        value.capacity_kwh,
        value.efficiency,
        value.wear_cost_ct,
        value.charge_ceiling_ct,
        value.minimum_net_saving_ct,
        value.forecast_today,
        value.forecast_tomorrow,
        value.pv_correction,
        value.current_price_ct,
    )
    if (
        not all(number(v) for v in parameters)
        or value.capacity_kwh <= 0
        or not 0 < value.efficiency <= 1
        or value.forecast_today < 0
        or value.forecast_tomorrow < 0
        or value.pv_correction < 0
    ):
        return "parameters_invalid"
    if (
        not number(value.minimum_price_advantage_percent)
        or not 0 <= value.minimum_price_advantage_percent <= 100
    ):
        return "price_advantage_invalid"
    if not value.prices:
        return "price_gap"
    previous = None
    current_start = int(value.now.timestamp() // 900) * 900
    current = None
    for point in value.prices:
        if not aware(point.starts_at) or not number(point.price_ct):
            return "price_data_invalid"
        ts = point.starts_at.timestamp()
        if ts % 900 != 0 or (previous is not None and ts <= previous):
            return "price_gap"
        previous = ts
        if ts == current_start:
            current = point.price_ct
    if current is None:
        return "price_gap"
    if abs(current - value.current_price_ct) >= 0.051:
        return "current_price_mismatch"
    return None


def common_target(batteries, capacities, grid_kwh: float) -> float:
    """Lowest whole-percent shared reserve whose grid charge covers grid_kwh."""

    def charged(level):
        return sum(
            c * max(level - b.soc, 0) / 100 for c, b in zip(capacities, batteries, strict=True)
        )

    low, high = 0.0, 100.0
    for _ in range(40):
        middle = (low + high) / 2
        low, high = (middle, high) if charged(middle) < grid_kwh else (low, middle)
    return float(min(100, ceil(high - EPSILON)))


def decide(value: PlannerInput) -> PlanResult:
    """Pure proposal only; session persistence and commands belong to the adapter."""
    invalid = _reason(value)
    if invalid:
        return PlanResult(False, invalid, 0.0, 0.0, 0.0, 0.0, None)
    capacities = [b.capacity_kwh or value.capacity_kwh for b in value.batteries]
    missing = sum(
        c * max(100 - b.soc, 0) / 100 for c, b in zip(capacities, value.batteries, strict=True)
    )
    curve = build_curve(value)
    if (
        not curve.valid
        or not number(curve.surplus_kwh)
        or any(not number(r.solar) or not number(r.load) for r in curve.rows)
    ):
        return PlanResult(
            False,
            "forecast_profile_invalid",
            missing,
            0.0,
            0.0,
            0.0,
            None,
            solar_day=curve.solar_day,
        )
    root = sqrt(value.efficiency)
    solar = curve.surplus_kwh
    # Only the part the expected PV surplus cannot cover comes from the grid.
    grid = max(missing - solar, 0.0)
    if not number(grid):
        return PlanResult(
            False, "projection_invalid", 0.0, 0.0, 0.0, 0.0, None, solar_day=curve.solar_day
        )
    target_soc = common_target(value.batteries, capacities, grid)
    if value.active_session:
        # While the cheap window lasts, hold what is stored: the house runs on the grid.
        target_soc = max(target_soc, float(floor(min(b.soc for b in value.batteries))))
    target = grid * root
    baseline = sum(
        c * max(b.soc - b.reserve, 0) / 100 * root
        for c, b in zip(capacities, value.batteries, strict=True)
    )
    if not all(number(n) for n in (missing, target, baseline)):
        return PlanResult(
            False, "projection_invalid", 0.0, 0.0, 0.0, 0.0, None, solar_day=curve.solar_day
        )
    prices = {p.starts_at.timestamp(): p.price_ct for p in value.prices}
    current = value.current_price_ct
    covered, total, gap = 0.0, 0.0, False
    for row in curve.rows[1:]:
        if covered >= target:
            break
        ts = row.ts
        if ts not in prices:
            gap = ts <= max(prices)
            break
        deficit = max(row.load - row.solar, 0)
        prior = min(baseline, deficit)
        baseline -= prior
        take = min(deficit - prior, target - covered)
        covered += take
        total += take * prices[ts]
    avoided = total / covered if covered > 0 else 0.0
    fraction = min(covered / target, 1) if target > 0 else 0.0
    cost = current / value.efficiency + value.wear_cost_ct
    net = (avoided - cost) * fraction
    advantage = (avoided - current) / avoided * 100 if avoided > 0 else None
    if not all(number(n) for n in (covered, avoided, fraction, cost, net)) or (
        advantage is not None and not number(advantage)
    ):
        return PlanResult(
            False, "projection_invalid", 0.0, 0.0, 0.0, 0.0, None, solar_day=curve.solar_day
        )
    reason = "eligible"
    if value.full_marker_for_solar_day:
        reason = "already_full_for_solar_day"
    elif missing <= 0:
        reason = "batteries_full"
    elif current > value.charge_ceiling_ct:
        reason = "price_above_ceiling"
    elif not value.active_session and grid <= 0:
        reason = "solar_surplus_sufficient"
    elif not value.best_price_window:
        reason = "outside_best_price_window"
    elif value.active_session and grid <= 0:
        # Grid share done; keep the session holding the reserve until the window ends.
        reason = "target_reached"
    elif gap:
        reason = "price_gap"
    elif covered <= 0:
        reason = "insufficient_priced_consumption"
    elif not 0 <= value.minimum_price_advantage_percent <= 100:
        reason = "price_advantage_invalid"
    elif avoided <= 0:
        reason = "nonpositive_reference_price"
    elif advantage + EPSILON < value.minimum_price_advantage_percent:
        reason = "price_advantage_too_low"
    elif net < value.minimum_net_saving_ct:
        reason = "net_saving_too_low"
    return PlanResult(
        reason in ("eligible", "target_reached"),
        reason,
        missing,
        solar,
        avoided,
        net,
        advantage,
        solar_day=curve.solar_day,
        coverage_kwh=covered,
        target_ac_kwh=target,
        coverage_fraction=fraction,
        cost_ct=cost,
        grid_kwh=grid,
        target_soc=target_soc,
    )
