"""Read-only HA snapshot and Recorder/Tibber boundaries; no source substitutions."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from homeassistant.exceptions import HomeAssistantError
from homeassistant.util import dt as dt_util

from .config_flow import SETTINGS
from .planner.core import (
    MAX_BATTERIES,
    PRICE_MAX_AGE,
    Battery,
    PlannerInput,
    PricePoint,
    build_hourly_profile,
    decide,
)
from .planner.forecast import solar_day as forecast_solar_day
from .storage import finite

_LOGGER = logging.getLogger(__name__)
# EcoFlow reports SOC about every minute. Commands use their own strict, post-intent
# readback in the runtime.
DEVICE_MAX_AGE = 600


def fresh(state, now, seconds):
    if state is None or state.state in ("unknown", "unavailable"):
        return False
    stamp = state.last_reported
    return stamp.tzinfo is not None and 0 <= (now - stamp).total_seconds() < seconds


def leader_reserve(hass, data, now):
    """Reserve entity of the system master: the only battery reporting a system load."""
    active = []
    for load, reserve in zip(
        data.get("sys_load_entities") or [], data.get("reserve_entities") or [], strict=False
    ):
        state = hass.states.get(load)
        try:
            if fresh(state, now, DEVICE_MAX_AGE) and float(state.state) > 0:
                active.append(reserve)
        except TypeError, ValueError:
            continue
    return active[0] if len(active) == 1 else None


def parse_prices(response, tariff):
    rows = response["prices"].get(tariff)
    if not isinstance(rows, list) or not rows:
        raise ValueError("selected_tariff_missing")
    result = []
    for row in rows:
        start = datetime.fromisoformat(row["start_time"])
        if start.tzinfo is None:
            raise ValueError("naive_price")
        result.append(PricePoint(start, finite(row["price"], -1000, 1000) * 100))
    return tuple(result)


def join_statistics(raw, keys, zone):
    """Keys are grid, PV, then n charge and n discharge energy statistics."""
    batteries, odd = divmod(len(keys) - 2, 2)
    if odd or not 1 <= batteries <= MAX_BATTERIES or len(set(keys)) != len(keys):
        raise ValueError("distinct_statistics_required")
    indexed = []
    for key in keys:
        series = {}
        duplicates = set()
        for row in raw.get(key, []):
            try:
                start = row["start"]
                if isinstance(start, str):
                    start = datetime.fromisoformat(start)
                elif isinstance(start, (float, int)) and not isinstance(start, bool):
                    start = datetime.fromtimestamp(start, UTC)
                if start.tzinfo is None:
                    continue
                start = start.astimezone(UTC)
                if start in series:
                    duplicates.add(start)
                    raise ValueError("duplicate_statistic")
                series[start] = finite(row["change"], -10 if key == keys[0] else 0, 10)
            except KeyError, TypeError, ValueError, AttributeError, OverflowError:
                continue
        for duplicate in duplicates:
            series.pop(duplicate, None)
        indexed.append(series)
    common = set(indexed[0]).intersection(*(set(s) for s in indexed[1:]))
    return [
        {
            "start": t.astimezone(zone),
            "grid": indexed[0][t],
            "pv": indexed[1][t],
            "charges": tuple(s[t] for s in indexed[2 : 2 + batteries]),
            "discharges": tuple(s[t] for s in indexed[2 + batteries :]),
        }
        for t in sorted(common)
    ]


async def hourly_changes(hass, keys, start, end):
    """Hourly energy changes in kWh; every key needs energy statistics."""
    from functools import partial

    from homeassistant.components.recorder import get_instance
    from homeassistant.components.recorder.statistics import get_metadata, statistics_during_period

    instance = get_instance(hass)
    metadata = await instance.async_add_executor_job(
        partial(get_metadata, hass, statistic_ids=set(keys))
    )
    if any(
        k not in metadata or metadata[k][1].get("unit_of_measurement") not in ("Wh", "kWh")
        for k in keys
    ):
        raise ValueError("statistics_unit_or_source_missing")
    return await instance.async_add_executor_job(
        statistics_during_period,
        hass,
        start.astimezone(UTC),
        end.astimezone(UTC),
        set(keys),
        "hour",
        {"energy": "kWh"},
        {"change"},
    )


async def read_statistics(hass, keys, start, end, zone):
    return join_statistics(await hourly_changes(hass, keys, start, end), keys, zone)


async def read_daily_pv(hass, entity, start, end):
    raw = await hourly_changes(hass, [entity], start, end)
    values = {}
    duplicates = set()
    for row in raw.get(entity, []):
        try:
            stamp = row["start"]
            if isinstance(stamp, str):
                stamp = datetime.fromisoformat(stamp).timestamp()
            elif isinstance(stamp, datetime):
                stamp = stamp.timestamp()
            if not start.timestamp() <= stamp < end.timestamp():
                continue
            if stamp in values:
                duplicates.add(stamp)
            values[stamp] = finite(row["change"], 0, 10)
        except ValueError, TypeError, KeyError:
            continue
    for stamp in duplicates:
        values.pop(stamp, None)
    return sum(values.values()), len(values)


class SourceReader:
    """One coordinated immutable planning input per refresh; live gates never cached."""

    def __init__(self, hass, entry, journal):
        self.hass, self.entry, self.journal = hass, entry, journal
        self.rows = []
        self.history_day = None
        self.prices = ()
        self.prices_fetched = None
        self.last_plan = None
        self.input = None
        self.error = None
        self._logged_error = None
        self.settings = {}

    @property
    def data(self):
        data = self.entry.data
        if data.get("pv_entity"):
            return data
        # No PV meter selected: use this entry's own integrated PV energy sensor.
        from .sources import own_pv_entity

        return {**data, "pv_entity": own_pv_entity(self.hass, self.entry.entry_id)}

    def trigger_ids(self):
        """Sources whose change can flip the charge decision at once.

        Meters, SOC and forecasts report every few seconds; the minute safety check and
        the quarter-hour plan cover them without a refresh per report.
        """
        data = self.entry.data
        result = [
            data[k]
            for k in ("price_window_entity", "price_entity", "sun_entity")
            if isinstance(data.get(k), str)
        ]
        for key in ("self_powered_entities", "reserve_entities"):
            if isinstance(data.get(key), list):
                result.extend(data[key])
        return result

    def numeric(self, key, now, age, *, low=0, high=1000, units=None):
        state = self.hass.states.get(key)
        if age is None:
            if state is None or state.state in ("unknown", "unavailable"):
                raise ValueError(f"source_unavailable: {key}")
        elif not fresh(state, now, age):
            raise ValueError(f"source_stale: {key}")
        if units is not None and state.attributes.get("unit_of_measurement") not in units:
            raise ValueError(f"source_unit_invalid: {key}")
        if units == {"kWh", "Wh"} and state.attributes.get("unit_of_measurement") == "Wh":
            # Energy always comes back in kWh.
            return finite(float(state.state), low * 1000, high * 1000) / 1000
        return finite(float(state.state), low, high)

    async def refresh(self):
        now = dt_util.now()
        data = self.data
        defaults = {key: spec[0] for key, spec in SETTINGS.items()}
        settings = {**defaults, **self.entry.options, **self.settings}
        gate = {
            "master": settings.get("master", False),
            "allowed": False,
            "valid": False,
            "full": False,
            "reason": "source_missing",
        }
        self.error = None
        # Full-SOC evidence is independent of tariff/profile health. A failed
        # economic refresh must not lose the session's mandatory full marker.
        try:
            socs = [
                self.numeric(e, now, DEVICE_MAX_AGE, high=100, units={"%"})
                for e in data["soc_entities"]
            ]
            gate["full"] = bool(socs) and all(s >= 100 for s in socs)
        except KeyError, ValueError, TypeError:
            pass
        try:
            keys = [
                data["grid_energy_entity"],
                data["pv_entity"],
                *data["charge_energy_entities"],
                *data["discharge_energy_entities"],
            ]
            midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
            if self.history_day != now.date():
                self.rows = await read_statistics(
                    self.hass, keys, midnight - timedelta(days=14), midnight, now.tzinfo
                )
                self.history_day = now.date()
            # Prices are published once a day; one fetch per hour picks up tomorrow's in time.
            hour = now.replace(minute=0, second=0, microsecond=0)
            if self.prices_fetched is None or hour > self.prices_fetched:
                response = await self.hass.services.async_call(
                    "tibber",
                    "get_prices",
                    {
                        "start": midnight.isoformat(),
                        "end": (midnight + timedelta(days=2) - timedelta(seconds=1)).isoformat(),
                    },
                    blocking=True,
                    return_response=True,
                )
                self.prices = parse_prices(response, data["tariff_key"])
                self.prices_fetched = now
            price_state = self.hass.states.get(data["price_entity"])
            current = self.numeric(
                data["price_entity"],
                now,
                PRICE_MAX_AGE,
                low=-100000,
                high=100000,
                units={"EUR/kWh", "ct/kWh"},
            )
            if price_state.attributes["unit_of_measurement"] == "EUR/kWh":
                current *= 100
            profile = build_hourly_profile(self.rows, now=now)
            soc = [
                self.numeric(e, now, DEVICE_MAX_AGE, high=100, units={"%"})
                for e in data["soc_entities"]
            ]
            original = self.journal.record.reserves_before if self.journal.record else {}
            reserves = [
                original.get(e)
                if e in original
                # EcoFlow reports the backup reserve only when it changes: no age limit.
                else self.numeric(e, now, None, low=3, high=100, units={"%"})
                for e in data["reserve_entities"]
            ]
            # Shadow never commands the devices, so it plans without the Self-powered gate;
            # active mode (and every start after switching to it) requires it.
            shadow = settings.get("mode", "shadow") == "shadow"
            protection = all(
                (s := self.hass.states.get(e)) is not None and s.state == "on"
                for e in data["self_powered_entities"]
            )
            window = self.hass.states.get(data["price_window_entity"])
            sun = self.hass.states.get(data["sun_entity"])
            if (
                not window
                or window.state not in ("on", "off")
                or not sun
                or sun.state not in ("below_horizon", "above_horizon")
            ):
                raise ValueError("unknown_window_or_sun")
            sunset = datetime.fromisoformat(sun.attributes["next_setting"])
            today = self.numeric(data["forecast_remaining_entity"], now, 3600, units={"kWh", "Wh"})
            tomorrow = self.numeric(
                data["forecast_tomorrow_entity"], now, 3600, units={"kWh", "Wh"}
            )
            solar_day = forecast_solar_day(now, sun.state == "below_horizon").isoformat()
            inp = PlannerInput(
                now=now,
                prices=self.prices,
                price_series_updated=price_state.last_reported,
                best_price_window=window.state == "on",
                profile=profile,
                forecast_today=today,
                forecast_tomorrow=tomorrow,
                pv_correction=self.journal.learning["correction"],
                sunset=sunset,
                batteries=tuple(
                    Battery(s, r, c)
                    for s, r, c in zip(
                        soc,
                        reserves,
                        data.get("capacities_kwh") or [None] * len(soc),
                        strict=True,
                    )
                ),
                capacity_kwh=settings["capacity_kwh"],
                efficiency=settings["efficiency"],
                wear_cost_ct=settings["wear_cost_ct"],
                charge_ceiling_ct=settings["charge_ceiling_ct"],
                minimum_net_saving_ct=settings["minimum_net_saving_ct"],
                minimum_price_advantage_percent=settings["minimum_price_advantage_percent"],
                active_session=self.journal.record is not None,
                full_marker_for_solar_day=self.journal.full_marker_day == solar_day,
                sources_fresh=True,
                protection_mode=protection or shadow,
                current_price_ct=current,
                below_horizon=sun.state == "below_horizon",
            )
            self.input = inp
            plan = decide(inp)
            self.last_plan = plan
            valid_reasons = {
                "eligible",
                "already_full_for_solar_day",
                "batteries_full",
                "price_above_ceiling",
                "solar_surplus_sufficient",
                "target_reached",
                "outside_best_price_window",
                "insufficient_priced_consumption",
                "nonpositive_reference_price",
                "price_advantage_too_low",
                "net_saving_too_low",
            }
            gate.update(
                allowed=plan.allowed,
                valid=profile.valid and (protection or shadow) and plan.reason in valid_reasons,
                self_powered=protection,
                full=all(s >= 100 for s in soc),
                solar_day=solar_day,
                reason=plan.reason,
                advantage=plan.price_advantage_percent,
                net_saving=plan.net_saving_ct,
                targets=dict.fromkeys(data["reserve_entities"], plan.target_soc)
                if plan.target_soc is not None
                else {},
                profile_valid=profile.valid,
            )
        except (
            KeyError,
            ValueError,
            TypeError,
            AttributeError,
            HomeAssistantError,
            LookupError,
            RuntimeError,
        ) as err:
            self.input = None
            self.last_plan = None
            self.error = gate["detail"] = f"{type(err).__name__}: {err}"
            if self.error != self._logged_error:
                _LOGGER.warning("Cannot plan, charging blocked: %s", self.error)
        self._logged_error = self.error
        return gate

    async def learn(self):
        # Called under the same runtime lock as planning, services and device commands.
        from dataclasses import asdict
        from datetime import date

        from .planner.learning import PVLearningState, capture_probe, learn_day

        now = dt_util.now()
        raw = self.journal.learning
        state = PVLearningState(
            tuple(raw["ratios"]),
            raw["correction"],
            date.fromisoformat(raw["probe_day"]) if raw["probe_day"] else None,
            raw["probe_kwh"],
            date.fromisoformat(raw["learned_day"]) if raw["learned_day"] else None,
        )
        data = self.data
        if (
            state.probe_day is not None
            and state.probe_day < now.date()
            and state.learned_day != state.probe_day
        ):
            # Resume the retained completed day even if HA missed the next-day window.
            start = datetime.combine(state.probe_day, datetime.min.time(), tzinfo=now.tzinfo)
            actual, count = await read_daily_pv(
                self.hass, data["pv_entity"], start, start + timedelta(days=1)
            )
            # Late statistics may still complete a day; one still short after a week never
            # will, so close it without a ratio and let the next probe start.
            if count >= 23 or state.probe_day < now.date() - timedelta(days=7):
                state = learn_day(state, day=state.probe_day, actual_kwh=actual, hourly_rows=count)
        if now.hour >= 5:
            try:
                forecast = self.numeric(
                    data["forecast_today_entity"], now, 3600, units={"kWh", "Wh"}
                )
                state = capture_probe(state, day=now.date(), forecast_kwh=forecast)
            except KeyError, ValueError, TypeError:
                pass
        result = asdict(state)
        for key in ("probe_day", "learned_day"):
            if result[key] is not None:
                result[key] = result[key].isoformat()
        await self.journal.async_set_learning(result)
