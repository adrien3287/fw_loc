"""Constants for FW Locations."""

DOMAIN = "fw_loc"
SOURCE = "fw_loc"

CONF_RADIUS_KM = "radius_km"
CONF_FIRE_STATIONS = "fire_stations"
CONF_HOSPITALS = "hospitals"
CONF_AMBULANCE_STATIONS = "ambulance_stations"

DEFAULT_RADIUS_KM = 50.0
MAX_RADIUS_KM = 50.0
MIN_RADIUS_KM = 1.0

DEFAULT_FIRE_STATIONS = True
DEFAULT_HOSPITALS = True
DEFAULT_AMBULANCE_STATIONS = True

UPDATE_INTERVAL_HOURS = 6

CATEGORY_FIRE_STATION = "fire_station"
CATEGORY_HOSPITAL = "hospital"
CATEGORY_AMBULANCE_STATION = "ambulance_station"

PROJECT_URL = "https://github.com/adrien3287/fw_loc"
VERSION = "0.2.0"
USER_AGENT = f"fw_loc/{VERSION} (+{PROJECT_URL})"

OVERPASS_ENDPOINTS = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
)
