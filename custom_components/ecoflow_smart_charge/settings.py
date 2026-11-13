"""Canonical economic policy heuristics, separate from saved advanced values."""

SETTINGS = {
    "minimum_price_advantage_percent": (20.0, 0, 100),
    "charge_ceiling_ct": (32.0, -100, 1000),
    "efficiency": (0.85, 0.01, 1),
    "wear_cost_ct": (2.0, 0, 100),
    "minimum_net_saving_ct": (3.0, 0, 1000),
    "capacity_kwh": (1.92, 0.01, 100),
}
SETTINGS_MODES = ("simple", "advanced")
CHARGING_POLICIES = {"save_more": 1.0, "balanced": 3.0, "protect_battery": 6.0}
POLICY_FIELDS = frozenset({"minimum_net_saving_ct", "minimum_price_advantage_percent"})
NEW_ENTRY_OPTIONS = {"settings_mode": "simple", "charging_policy": "balanced"}


def effective_settings(options):
    """Resolve heuristics per delivered kWh; absent mode keeps legacy economics."""
    result = {key: spec[0] for key, spec in SETTINGS.items()}
    result.update(settings_mode="advanced", charging_policy="balanced")
    result.update(options)
    if result["settings_mode"] == "simple":
        result["minimum_net_saving_ct"] = CHARGING_POLICIES[result["charging_policy"]]
        result["minimum_price_advantage_percent"] = 0.0
    return result


def merge_settings(options, updates):
    """Validate every write and make numerical threshold edits effective immediately."""
    from .config_flow import validate_settings

    validate_settings(updates)
    updates = dict(updates)
    if POLICY_FIELDS.intersection(updates):
        if updates.get("settings_mode") == "simple":
            raise ValueError("invalid_setting")
        updates["settings_mode"] = "advanced"
    return {**options, **updates}
