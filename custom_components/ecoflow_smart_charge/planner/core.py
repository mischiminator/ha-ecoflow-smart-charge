"""HA-free planning primitives; no Home Assistant or I/O imports are permitted."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from statistics import median
from typing import Iterable

EPSILON = 1e-9


@dataclass(frozen=True)
class Battery:
    soc: float
    reserve: float


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
    batteries: tuple[Battery, Battery, Battery]
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


def build_hourly_profile(rows: Iterable[dict[str, object]]) -> HourlyProfile:
    """Reconstruct load: grid net + PV - all charging + all discharge."""
    buckets: list[list[tuple[float, float]]] = [[] for _ in range(24)]
    for row in rows:
        try:
            stamp = row["start"]
            if not isinstance(stamp, datetime):
                continue
            grid = float(row["grid"])
            pv = float(row["pv"])
            charges = tuple(float(v) for v in row["charges"])  # type: ignore[arg-type]
            discharges = tuple(float(v) for v in row["discharges"])  # type: ignore[arg-type]
        except (KeyError, TypeError, ValueError):
            continue
        load = grid + pv - sum(charges) + sum(discharges)
        if grid < 0 or pv < 0 or load < 0 or load > 10 or pv > 10:
            continue
        buckets[stamp.hour].append((load, pv))
    counts = tuple(len(bucket) for bucket in buckets)
    valid = min(counts, default=0) >= 3
    return HourlyProfile(
        house_by_hour=tuple(sum(v[0] for v in b) / len(b) if b else 0.0 for b in buckets),
        pv_by_hour=tuple(sum(v[1] for v in b) / len(b) if b else 0.0 for b in buckets),
        samples_by_hour=counts,
        valid=valid,
        reason="ok" if valid else "insufficient_hourly_samples",
    )


def learn_pv_correction(
    ratios: list[float], *, actual_kwh: float, forecast_kwh: float, hourly_rows: int
) -> tuple[float, ...]:
    """Append one valid daily ratio, retaining only the newest fourteen."""
    if hourly_rows < 23 or forecast_kwh <= 0:
        return tuple(ratios[-14:])
    ratio = actual_kwh / forecast_kwh
    if not 0 <= ratio <= 5:
        return tuple(ratios[-14:])
    return tuple((ratios + [ratio])[-14:])


def correction_from_ratios(ratios: Iterable[float]) -> float | None:
    clean = [ratio for ratio in ratios if 0 <= ratio <= 5]
    return median(clean[-14:]) if len(clean) >= 3 else None


def _reason(value: PlannerInput) -> str | None:
    if not value.sources_fresh:
        return "sources_stale"
    if not value.profile.valid:
        return "profile_invalid"
    if not value.protection_mode:
        return "protection_mode_required"
    if value.now - value.price_series_updated > timedelta(minutes=15):
        return "prices_stale"
    if len(value.prices) < 2 or not _continuous_prices(value.prices, value.now):
        return "price_gap"
    if any(not 0 <= b.soc <= 100 or not 0 <= b.reserve <= 100 for b in value.batteries):
        return "battery_data_invalid"
    if value.capacity_kwh <= 0 or not 0 < value.efficiency <= 1:
        return "parameters_invalid"
    if value.full_marker_for_solar_day:
        return "already_full_for_solar_day"
    return None


def _continuous_prices(prices: tuple[PricePoint, ...], now: datetime) -> bool:
    ordered = sorted(prices, key=lambda point: point.starts_at)
    if ordered[0].starts_at != now:
        return False
    # Tibber series may be hourly or quarter-hourly. Gaps beyond one nominal interval fail closed.
    spacing = ordered[1].starts_at - ordered[0].starts_at
    if spacing <= timedelta(0) or spacing > timedelta(hours=1):
        return False
    return all(b.starts_at - a.starts_at == spacing for a, b in zip(ordered, ordered[1:]))


def decide(value: PlannerInput) -> PlanResult:
    """Produce a shadow-only plan. Runtime owns all actual hardware commands."""
    invalid = _reason(value)
    missing = sum(value.capacity_kwh * max(100 - battery.soc, 0) / 100 for battery in value.batteries)
    if invalid:
        return PlanResult(False, invalid, missing, 0.0, 0.0, 0.0, None)
    current = value.prices[0].price_ct
    solar = _solar_surplus(value)
    future = sorted(value.prices[1:], key=lambda p: p.starts_at)
    required = missing
    covered, avoided = _weighted_avoided_price(value.profile, future, required)
    if missing <= 0:
        return PlanResult(False, "batteries_full", missing, solar, avoided, 0.0, None)
    if current > value.charge_ceiling_ct:
        return PlanResult(False, "price_above_ceiling", missing, solar, avoided, 0.0, None)
    if not value.active_session and solar >= missing:
        return PlanResult(False, "solar_surplus_sufficient", missing, solar, avoided, 0.0, None)
    if not value.best_price_window:
        return PlanResult(False, "outside_best_price_window", missing, solar, avoided, 0.0, None)
    if not covered or avoided <= 0:
        return PlanResult(False, "insufficient_priced_consumption", missing, solar, avoided, 0.0, None)
    advantage = (avoided - current) / avoided * 100
    if not 0 <= value.minimum_price_advantage_percent <= 100:
        return PlanResult(False, "price_advantage_invalid", missing, solar, avoided, 0.0, advantage)
    if advantage + EPSILON < value.minimum_price_advantage_percent:
        return PlanResult(False, "price_advantage_too_low", missing, solar, avoided, 0.0, advantage)
    net = avoided - (current / value.efficiency + value.wear_cost_ct)
    if net < value.minimum_net_saving_ct:
        return PlanResult(False, "net_saving_too_low", missing, solar, avoided, net, advantage)
    return PlanResult(True, "eligible_shadow_plan", missing, solar, avoided, net, advantage)


def _solar_surplus(value: PlannerInput) -> float:
    if not 0 <= value.pv_correction <= 5:
        return 0.0
    forecast = value.forecast_today if value.now < value.sunset else value.forecast_tomorrow
    if forecast < 0:
        return 0.0
    total_profile_pv = sum(value.profile.pv_by_hour)
    if total_profile_pv <= 0:
        return 0.0
    share = forecast * value.pv_correction / total_profile_pv
    return sum(max(pv * share - load, 0.0) for pv, load in zip(value.profile.pv_by_hour, value.profile.house_by_hour))


def _weighted_avoided_price(profile: HourlyProfile, prices: list[PricePoint], required: float) -> tuple[bool, float]:
    remaining = required
    total_cost = 0.0
    for point in prices:
        demand = profile.house_by_hour[point.starts_at.hour]
        used = min(demand, remaining)
        total_cost += used * point.price_ct
        remaining -= used
        if remaining <= EPSILON:
            return True, total_cost / required
    return False, total_cost / required if required else 0.0
