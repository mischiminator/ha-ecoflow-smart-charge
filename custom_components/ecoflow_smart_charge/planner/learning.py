"""Immutable PV-learning transitions. The adapter supplies completed day evidence."""

from dataclasses import dataclass, replace
from datetime import date
from statistics import median

from .validation import number


@dataclass(frozen=True)
class PVLearningState:
    ratios: tuple[float, ...]
    correction: float
    probe_day: date | None
    probe_kwh: float | None
    learned_day: date | None


def capture_probe(state: PVLearningState, *, day: date, forecast_kwh: float) -> PVLearningState:
    if not number(forecast_kwh) or forecast_kwh <= 0:
        return state
    if state.probe_day is not None and (
        day <= state.probe_day or state.learned_day != state.probe_day
    ):
        return state
    if state.learned_day is not None and day <= state.learned_day:
        return state
    return replace(state, probe_day=day, probe_kwh=forecast_kwh)


def learn_day(
    state: PVLearningState, *, day: date, actual_kwh: float, hourly_rows: int
) -> PVLearningState:
    if state.probe_day != day or (state.learned_day is not None and day <= state.learned_day):
        return state
    ratios = learn_pv_correction(
        list(state.ratios),
        actual_kwh=actual_kwh,
        forecast_kwh=state.probe_kwh,
        hourly_rows=hourly_rows,
    )
    correction = correction_from_ratios(ratios)
    return replace(
        state, ratios=ratios, correction=1.0 if correction is None else correction, learned_day=day
    )


def learn_pv_correction(
    ratios: list[float], *, actual_kwh: float, forecast_kwh: float, hourly_rows: int
) -> tuple[float, ...]:
    prior = tuple(ratios[-14:])
    if (
        not isinstance(hourly_rows, int)
        or isinstance(hourly_rows, bool)
        or hourly_rows < 23
        or not number(actual_kwh)
        or not number(forecast_kwh)
        or forecast_kwh <= 0
    ):
        return prior
    ratio = actual_kwh / forecast_kwh
    return (*prior, ratio)[-14:] if 0 <= ratio <= 5 else prior


def correction_from_ratios(ratios) -> float | None:
    clean = [r for r in ratios if number(r) and 0 <= r <= 5][-14:]
    return median(clean) if len(clean) >= 3 else None
