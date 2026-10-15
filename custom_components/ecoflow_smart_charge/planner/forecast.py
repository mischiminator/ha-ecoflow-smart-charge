"""Live-formula 196 quarter-hour curve; elapsed seconds, local calendar days."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from math import sqrt


@dataclass(frozen=True)
class Interval:
    ts: int
    load: float
    solar: float
    daylight: bool


@dataclass(frozen=True)
class SolarCurve:
    solar_day: str
    rows: tuple[Interval, ...]
    surplus_kwh: float
    valid: bool


def build_curve(value) -> SolarCurve:
    today = value.now.date()
    tomorrow = today + timedelta(days=1)
    solar_day = tomorrow if value.below_horizon and value.now.hour >= 12 else today
    now_ts = value.now.timestamp()
    start = int(now_ts // 900) * 900
    raw = []
    denominators = {today: 0.0, tomorrow: 0.0}
    for i in range(196):
        ts = start + i * 900
        dt = datetime.fromtimestamp(ts, value.now.tzinfo)
        fraction = min(ts + 900 - now_ts, 900) / 3600 if i == 0 else 0.25
        score = value.profile.pv_by_hour[dt.hour] * fraction
        if dt.date() in denominators:
            denominators[dt.date()] += score
        raw.append((ts, dt.date(), score, value.profile.house_by_hour[dt.hour] * fraction))
    forecasts = {today: value.forecast_today, tomorrow: value.forecast_tomorrow}
    valid = all(denominators[d] > 0 or forecasts[d] == 0 for d in denominators)
    rows, surplus = [], 0.0
    for ts, day, score, load in raw:
        solar = (
            forecasts[day] * value.pv_correction * score / denominators[day]
            if day in denominators and denominators[day] > 0
            else 0.0
        )
        daylight = day == solar_day and ts < value.sunset.timestamp()
        if daylight:
            surplus += max(solar - load, 0) * sqrt(value.efficiency)
        rows.append(Interval(ts, load, solar, daylight))
    return SolarCurve(solar_day.isoformat(), tuple(rows), surplus, valid)
