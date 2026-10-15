"""Constants for EcoFlow Smart Charge."""

DOMAIN = "ecoflow_smart_charge"
PLATFORMS = ("sensor", "binary_sensor", "number", "select", "switch", "button")
MODE_SHADOW = "shadow"
MODE_ARMED = "armed"
MODE_ACTIVE = "active"
DEFAULT_MINIMUM_PRICE_ADVANTAGE = 20.0
DEFAULT_CHARGE_CEILING_CT = 32.0
DEFAULT_EFFICIENCY = 0.85
DEFAULT_WEAR_COST_CT = 2.0
DEFAULT_MINIMUM_NET_SAVING_CT = 3.0
STORE_VERSION = 1
