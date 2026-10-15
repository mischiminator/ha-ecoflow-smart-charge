"""Planning diagnostics; missing inputs remain unknown."""

from homeassistant.components.sensor import SensorEntity

from .entity import RuntimeEntity

KEYS = {
    "status": "Controller status",
    "reason": "Decision reason",
    "missing_energy_kwh": "Missing energy",
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
        if key.endswith("_kwh"):
            self._attr_native_unit_of_measurement = "kWh"
        elif key.endswith("_ct"):
            self._attr_native_unit_of_measurement = "ct/kWh"
        elif key == "price_advantage_percent":
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


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([PlanSensor(entry, key, name) for key, name in KEYS.items()])
