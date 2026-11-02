"""Planning diagnostics; missing inputs remain unknown."""

from datetime import timedelta

from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.core import callback
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_interval
from homeassistant.util import dt as dt_util

from .entity import RuntimeEntity
from .sources import OWN_PV_KEY
from .storage import finite

# Longer gaps (HA stalled or stopped) are skipped instead of extrapolated.
MAX_GAP = timedelta(minutes=10)

KEYS = {
    "status": "Controller status",
    "reason": "Decision reason",
    "missing_energy_kwh": "Missing energy",
    "grid_kwh": "Grid charge energy",
    "target_soc": "Grid charge target",
    "solar_surplus_kwh": "Solar surplus",
    "avoided_price_ct": "Avoided price",
    "net_saving_ct": "Net saving",
    "price_advantage_percent": "Price advantage",
    "pv_correction": "PV correction",
    "full_marker_day": "Full marker day",
    "solar_day": "Planned solar day",
    "plan_updated": "Plan updated",
    "profile_samples": "Profile samples",
    "corrected_forecast_kwh": "Corrected solar forecast",
}


class PlanSensor(RuntimeEntity, SensorEntity):
    def __init__(self, entry, key, name):
        super().__init__(entry, key, name)
        if key.endswith("_kwh") or key == "grid_kwh":
            self._attr_native_unit_of_measurement = "kWh"
        elif key.endswith("_ct"):
            self._attr_native_unit_of_measurement = "ct/kWh"
        elif key in ("price_advantage_percent", "target_soc"):
            self._attr_native_unit_of_measurement = "%"

    @property
    def native_value(self):
        if self.key == "status":
            return self.runtime.status
        if self.key == "reason":
            return (self.runtime.last_snapshot or {}).get("reason")
        if self.key == "pv_correction":
            return self.runtime.journal.learning["correction"]
        if self.key == "full_marker_day":
            return self.runtime.journal.full_marker_day
        inp = self.runtime.reader.input
        if self.key == "plan_updated":
            return inp.now.isoformat() if inp else None
        if self.key == "profile_samples":
            return min(inp.profile.samples_by_hour) if inp else None
        if self.key == "corrected_forecast_kwh":
            if not inp:
                return None
            forecast = (
                inp.forecast_tomorrow
                if inp.below_horizon and inp.now.hour >= 12
                else inp.forecast_today
            )
            return forecast * inp.pv_correction
        plan = self.runtime.reader.last_plan
        return getattr(plan, self.key, None) if plan else None


class PVEnergySensor(RuntimeEntity, RestoreSensor):
    """Left Riemann sum of the batteries' EcoFlow PV power readings; replaces a user helper."""

    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = "kWh"
    _attr_suggested_display_precision = 3

    def __init__(self, entry):
        super().__init__(entry, OWN_PV_KEY, "PV energy")
        self.sources = tuple(entry.data["pv_power_entities"])
        self.total = 0.0
        self.watts = None
        self.since = None

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        last = await self.async_get_last_sensor_data()
        try:
            self.total = finite(float(last.native_value), 0, 1e9)
        except AttributeError, TypeError, ValueError:
            self.total = 0.0
        self._sample()
        self.async_on_remove(async_track_state_change_event(self.hass, self.sources, self._update))
        # Flush the held power regularly so hourly statistics see current energy.
        self.async_on_remove(
            async_track_time_interval(self.hass, self._update, timedelta(minutes=1))
        )

    def _power(self):
        total = 0.0
        for entity in self.sources:
            state = self.hass.states.get(entity)
            try:
                scale = {"W": 1, "kW": 1000}[state.attributes.get("unit_of_measurement")]
                total += finite(float(state.state), 0, 100000) * scale
            except AttributeError, KeyError, TypeError, ValueError:
                return None
        return total

    def _sample(self):
        now = dt_util.utcnow()
        if self.watts is not None and timedelta(0) < now - self.since <= MAX_GAP:
            self.total += self.watts * (now - self.since).total_seconds() / 3600000
        # An unavailable source leaves its interval unintegrated rather than guessed.
        self.watts, self.since = self._power(), now

    @callback
    def _update(self, _event=None):
        self._sample()
        self.async_write_ha_state()

    @property
    def native_value(self):
        return round(self.total, 4)


async def async_setup_entry(hass, entry, async_add_entities):
    entities = [PlanSensor(entry, key, name) for key, name in KEYS.items()]
    if not entry.data.get("pv_entity") and entry.data.get("pv_power_entities"):
        entities.append(PVEnergySensor(entry))
    async_add_entities(entities)
