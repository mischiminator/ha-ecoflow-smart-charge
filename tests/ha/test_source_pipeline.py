"""Full source-to-plan path and daily learning, with actual hass states/services."""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from homeassistant.core import SupportsResponse
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ecoflow_smart_charge.const import DOMAIN


def data_states(hass, now):
    data = {
        "grid_energy_entity": "sensor.grid",
        "pv_entity": "sensor.pv",
        "price_entity": "sensor.price",
        "price_window_entity": "binary_sensor.window",
        "sun_entity": "sun.test",
        "tariff_key": "Chosen",
        "forecast_today_entity": "sensor.forecast",
        "forecast_remaining_entity": "sensor.remaining",
        "forecast_tomorrow_entity": "sensor.tomorrow",
    }
    for kind, domain, value, unit in [
        ("soc", "sensor", "50", "%"),
        ("reserve", "number", "13", "%"),
        ("self_powered", "switch", "on", None),
        ("charge_energy", "sensor", "1", "kWh"),
        ("discharge_energy", "sensor", "1", "kWh"),
    ]:
        data[kind + "_entities"] = [f"{domain}.{kind}_{i}" for i in range(3)]
        for e in data[kind + "_entities"]:
            hass.states.async_set(e, value, {"unit_of_measurement": unit} if unit else {})
    for e in ("sensor.grid", "sensor.pv", "sensor.forecast", "sensor.remaining", "sensor.tomorrow"):
        hass.states.async_set(
            e, "0" if e != "sensor.forecast" else "4", {"unit_of_measurement": "kWh"}
        )
    hass.states.async_set("sensor.price", "0.10", {"unit_of_measurement": "EUR/kWh"})
    hass.states.async_set("binary_sensor.window", "on")
    hass.states.async_set(
        "sun.test", "above_horizon", {"next_setting": (now + timedelta(hours=6)).isoformat()}
    )
    return data


async def test_source_to_plan_selects_tariff_and_fails_closed_on_wrong_home(hass):
    from custom_components.ecoflow_smart_charge.reader import SourceReader
    from custom_components.ecoflow_smart_charge.storage import PersistentSessionStore

    class Disk:
        async def async_save(self, data):
            self.data = data

    now = datetime.now(UTC)
    data = data_states(hass, now)
    entry = MockConfigEntry(domain=DOMAIN, data=data, options={"master": True})
    journal = PersistentSessionStore(Disk())
    reader = SourceReader(hass, entry, journal)
    rows = [
        {
            "start": (now - timedelta(days=d)).replace(hour=h, minute=0, second=0, microsecond=0),
            "grid": 2.0,
            "pv": 0.0,
            "charges": (0.0, 0.0, 0.0),
            "discharges": (0.0, 0.0, 0.0),
        }
        for d in range(1, 15)
        for h in range(24)
    ]
    start = datetime.fromtimestamp(int(now.timestamp() // 900) * 900, UTC)

    async def prices(call):
        return {
            "prices": {
                "Chosen": [
                    {
                        "start_time": (start + timedelta(minutes=15 * i)).isoformat(),
                        "price": 0.10 if i == 0 else 0.50,
                    }
                    for i in range(192)
                ],
                "Wrong": [{"start_time": start.isoformat(), "price": 9}],
            }
        }

    hass.services.async_register(
        "tibber", "get_prices", prices, supports_response=SupportsResponse.ONLY
    )
    with patch("custom_components.ecoflow_smart_charge.reader.read_statistics", return_value=rows):
        result = await reader.refresh()
        assert result["valid"] and result["allowed"]
        # No PV surplus expected: every reserve is targeted to a full battery.
        assert result["targets"] == dict.fromkeys(data["reserve_entities"], 100.0)
        assert reader.input.current_price_ct == 10
        assert reader.input.prices[1].price_ct == 50
        # EcoFlow reports the reserve only every few minutes: a 190 s old reserve still plans.
        later = now + timedelta(seconds=190)
        with patch("custom_components.ecoflow_smart_charge.reader.dt_util.now", return_value=later):
            result = await reader.refresh()
        assert "detail" not in result and result["reason"] != "source_missing"
        # Prices are published once a day: fetched again only in the next hour.
        reader.prices_fetched = later.replace(minute=0, second=0, microsecond=0)
        kept = reader.prices
        with patch("custom_components.ecoflow_smart_charge.reader.dt_util.now", return_value=later):
            await reader.refresh()
        assert reader.prices is kept
        next_hour = later + timedelta(hours=1)
        with patch(
            "custom_components.ecoflow_smart_charge.reader.dt_util.now", return_value=next_hour
        ):
            await reader.refresh()
        assert reader.prices is not kept
        # The reserve is reported only when it changes: an hours-old value still plans.
        assert reader.numeric(data["reserve_entities"][0], now + timedelta(hours=5), None) == 13
        hass.states.async_set(data["reserve_entities"][0], "unavailable")
        with pytest.raises(ValueError, match="source_unavailable"):
            reader.numeric(data["reserve_entities"][0], now, None)
        hass.states.async_set(data["reserve_entities"][0], "13", {"unit_of_measurement": "%"})
        # Beyond the device age the blocking source is named and logged once.
        stale = now + timedelta(seconds=700)
        with (
            patch("custom_components.ecoflow_smart_charge.reader.dt_util.now", return_value=stale),
            patch("custom_components.ecoflow_smart_charge.reader._LOGGER") as logger,
        ):
            first = await reader.refresh()
            second = await reader.refresh()
        assert first["detail"] == "ValueError: source_stale: sensor.soc_0"
        assert second["detail"] == first["detail"] and not second["valid"]
        logger.warning.assert_called_once()
        reader.entry = MockConfigEntry(domain=DOMAIN, data={**data, "tariff_key": "Missing"})
        reader.prices_fetched = None
        assert not (await reader.refresh())["valid"]


async def test_learning_persists_probe_then_learns_yesterday_before_new_probe(hass, freezer):
    # Probes start at 05:00; a fixed noon keeps the test independent of the wall clock.
    freezer.move_to("2026-06-02T12:00:00+00:00")
    from custom_components.ecoflow_smart_charge.reader import SourceReader
    from custom_components.ecoflow_smart_charge.storage import PersistentSessionStore

    class Disk:
        def __init__(self):
            self.data = None

        async def async_save(self, data):
            self.data = data

    disk = Disk()
    journal = PersistentSessionStore(disk)
    now = datetime.now(UTC)
    data = data_states(hass, now)
    reader = SourceReader(hass, MockConfigEntry(domain=DOMAIN, data=data), journal)
    now = datetime.now(UTC)
    yesterday = (now.date() - timedelta(days=1)).isoformat()
    await journal.async_set_learning(
        {
            "ratios": [1, 1, 1],
            "correction": 1,
            "probe_day": yesterday,
            "probe_kwh": 4.0,
            "learned_day": None,
        }
    )
    with (
        patch(
            "custom_components.ecoflow_smart_charge.reader.read_daily_pv", return_value=(6.0, 24)
        ),
        patch("custom_components.ecoflow_smart_charge.reader.dt_util.now", return_value=now),
    ):
        await reader.learn()
        assert journal.learning["learned_day"] == yesterday
        assert journal.learning["ratios"][-1] == 1.5
        assert journal.learning["probe_day"] == now.date().isoformat()
        assert disk.data["learning"] == journal.learning


async def test_full_soc_is_retained_for_marker_even_if_tariff_fails(hass):
    from custom_components.ecoflow_smart_charge.reader import SourceReader
    from custom_components.ecoflow_smart_charge.storage import PersistentSessionStore

    now = datetime.now(UTC)
    data = data_states(hass, now)
    for e in data["soc_entities"]:
        hass.states.async_set(e, "100", {"unit_of_measurement": "%"})
    reader = SourceReader(
        hass, MockConfigEntry(domain=DOMAIN, data=data), PersistentSessionStore(None)
    )
    with patch(
        "custom_components.ecoflow_smart_charge.reader.read_statistics",
        side_effect=KeyError("no recorder"),
    ):
        result = await reader.refresh()
        assert not result["valid"]
        assert result["full"]


async def test_shadow_plans_without_self_powered_but_active_requires_it(hass):
    from custom_components.ecoflow_smart_charge.reader import SourceReader
    from custom_components.ecoflow_smart_charge.storage import PersistentSessionStore

    class Disk:
        async def async_save(self, data):
            self.data = data

    now = datetime.now(UTC)
    data = data_states(hass, now)
    for entity in data["self_powered_entities"]:
        hass.states.async_set(entity, "off")
    start = datetime.fromtimestamp(int(now.timestamp() // 900) * 900, UTC)

    async def prices(call):
        rows = [
            {"start_time": (start + timedelta(minutes=15 * i)).isoformat(), "price": 0.10}
            for i in range(192)
        ]
        return {"prices": {"Chosen": rows}}

    hass.services.async_register(
        "tibber", "get_prices", prices, supports_response=SupportsResponse.ONLY
    )
    rows = [
        {
            "start": (now - timedelta(days=d)).replace(hour=h, minute=0, second=0, microsecond=0),
            "grid": 2.0,
            "pv": 0.0,
            "charges": (0.0, 0.0, 0.0),
            "discharges": (0.0, 0.0, 0.0),
        }
        for d in range(1, 15)
        for h in range(24)
    ]
    with patch("custom_components.ecoflow_smart_charge.reader.read_statistics", return_value=rows):
        for mode, reason_blocked in (("shadow", False), ("active", True)):
            entry = MockConfigEntry(
                domain=DOMAIN, data=data, options={"master": True, "mode": mode}
            )
            reader = SourceReader(hass, entry, PersistentSessionStore(Disk()))
            gate = await reader.refresh()
            assert gate["self_powered"] is False
            assert (gate["reason"] == "protection_mode_required") is reason_blocked, mode
            assert gate["valid"] is not reason_blocked, mode
