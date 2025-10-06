"""Constants for the Prana BLE integration."""

from datetime import timedelta

DOMAIN = "prana_ble"
PLATFORMS: list[str] = [
    "fan",
    "sensor",
    "number",
    "select",
    "switch",
]

DEFAULT_UPDATE_INTERVAL = 30

SERVICE_UUID = "000000ee-0000-1000-8000-00805f9b34fb"
DEVICE_NAME_PREFIXES = ["PRNAQaq", "PRANA", "PRNBYav"]

CONF_MAX_SPEED = "max_speed"
CONF_UPDATE_INTERVAL = "update_interval"

DEVICE_MANUFACTURER = "Prana"
DEVICE_FALLBACK = "Prana BLE"

DEFAULT_MAX_SPEED = 5

