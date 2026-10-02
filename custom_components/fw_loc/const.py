"""Constants for FW Locations."""

DOMAIN = "fw_loc"
SOURCE = "fw_loc"

CONF_RADIUS_KM = "radius_km"
CONF_FIRE_STATIONS = "fire_stations"
CONF_HOSPITALS = "hospitals"
CONF_AMBULANCE_STATIONS = "ambulance_stations"
CONF_GENERAL_PRACTITIONERS = "general_practitioners"

DEFAULT_RADIUS_KM = 50.0
MAX_RADIUS_KM = 50.0
MIN_RADIUS_KM = 1.0

DEFAULT_FIRE_STATIONS = True
DEFAULT_HOSPITALS = True
DEFAULT_AMBULANCE_STATIONS = True
DEFAULT_GENERAL_PRACTITIONERS = True

UPDATE_INTERVAL_HOURS = 6

CATEGORY_FIRE_STATION = "fire_station"
CATEGORY_HOSPITAL = "hospital"
CATEGORY_AMBULANCE_STATION = "ambulance_station"
CATEGORY_GENERAL_PRACTITIONER = "general_practitioner"

OVERPASS_ENDPOINTS = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
)
