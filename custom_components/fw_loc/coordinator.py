"""Data coordinator for FW Locations."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import logging
from typing import Any

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util.location import distance

from .const import (
    CATEGORY_AMBULANCE_STATION,
    CATEGORY_FIRE_STATION,
    CATEGORY_HOSPITAL,
    CONF_AMBULANCE_STATIONS,
    CONF_FIRE_STATIONS,
    CONF_HOSPITALS,
    CONF_RADIUS_KM,
    DEFAULT_AMBULANCE_STATIONS,
    DEFAULT_FIRE_STATIONS,
    DEFAULT_HOSPITALS,
    DEFAULT_RADIUS_KM,
    DOMAIN,
    MAX_RADIUS_KM,
    OVERPASS_ENDPOINTS,
    PROJECT_URL,
    UPDATE_INTERVAL_HOURS,
    USER_AGENT,
)

_LOGGER = logging.getLogger(__name__)

_CACHE_VERSION = 3

_RETTUNGSWACHE_TERMS = (
    "rettungswache",
    "lehrrettungswache",
    "feuer- und rettungswache",
    "feuer und rettungswache",
    "rettungszentrum",
    "notfallrettung",
    "rettungsdienst",
)

_RECOGNIZED_RESCUE_ORGS = (
    "deutsches rotes kreuz",
    " drk ",
    "arbeiter-samariter-bund",
    "arbeiter samariter bund",
    " asb ",
    "johanniter",
    "malteser",
    "berufsfeuerwehr",
    "feuerwehr",
    "kreisrettungsdienst",
    "rettungsdienst",
)


@dataclass(slots=True)
class Place:
    """A mapped emergency or healthcare location."""

    unique_id: str
    osm_type: str
    osm_id: int
    category: str
    name: str
    latitude: float
    longitude: float
    distance_km: float
    tags: dict[str, str]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Place":
        """Create a place from cached data."""
        return cls(
            unique_id=str(data["unique_id"]),
            osm_type=str(data["osm_type"]),
            osm_id=int(data["osm_id"]),
            category=str(data["category"]),
            name=str(data["name"]),
            latitude=float(data["latitude"]),
            longitude=float(data["longitude"]),
            distance_km=float(data["distance_km"]),
            tags={str(k): str(v) for k, v in dict(data.get("tags", {})).items()},
        )


class FwLocCoordinator(DataUpdateCoordinator[list[Place]]):
    """Fetch nearby emergency and healthcare locations from OpenStreetMap."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(hours=UPDATE_INTERVAL_HOURS),
            always_update=True,
        )
        self.entry = entry
        self.store: Store[dict[str, Any]] = Store(
            hass,
            _CACHE_VERSION,
            f"{DOMAIN}.{entry.entry_id}",
        )
        self.using_cache = False
        self.data_updated_at: str | None = None

    def _option(self, key: str, default: Any) -> Any:
        """Read an option, falling back to initial config."""
        return self.entry.options.get(
            key,
            self.entry.data.get(key, default),
        )

    @property
    def radius_km(self) -> float:
        """Return configured radius, clamped to the integration hard maximum."""
        value = float(self._option(CONF_RADIUS_KM, DEFAULT_RADIUS_KM))
        return min(max(value, 1.0), MAX_RADIUS_KM)

    def _enabled(self, key: str, default: bool) -> bool:
        """Return whether a category is enabled."""
        return bool(self._option(key, default))

    async def _async_update_data(self) -> list[Place]:
        """Fetch data from Overpass, with local cache fallback."""
        latitude = float(self.hass.config.latitude)
        longitude = float(self.hass.config.longitude)
        radius_m = int(self.radius_km * 1000)

        query = self._build_query(radius_m, latitude, longitude)
        session = async_get_clientsession(self.hass)

        last_error: Exception | None = None
        for endpoint in OVERPASS_ENDPOINTS:
            try:
                places = await self._async_fetch_endpoint(
                    session,
                    endpoint,
                    query,
                    latitude,
                    longitude,
                )
                timestamp = datetime.now(timezone.utc).isoformat()
                self.using_cache = False
                self.data_updated_at = timestamp
                await self.store.async_save(
                    {
                        "updated_at": timestamp,
                        "places": [asdict(place) for place in places],
                    }
                )
                return places
            except (aiohttp.ClientError, TimeoutError, ValueError) as err:
                last_error = err
                _LOGGER.warning("Overpass endpoint %s failed: %s", endpoint, err)

        cached = await self.store.async_load()
        if cached and cached.get("places"):
            self.using_cache = True
            self.data_updated_at = str(cached.get("updated_at") or "")
            _LOGGER.warning(
                "Using cached FW Locations data because all Overpass endpoints failed"
            )
            places: list[Place] = []
            for item in cached["places"]:
                place = Place.from_dict(item)
                if (
                    _is_active_feature(place.tags)
                    and place.category in self._categories_for(place.tags)
                ):
                    places.append(place)
            return places

        raise UpdateFailed(
            f"Unable to retrieve OpenStreetMap data: {last_error}"
        ) from last_error

    async def _async_fetch_endpoint(
        self,
        session: aiohttp.ClientSession,
        endpoint: str,
        query: str,
        home_latitude: float,
        home_longitude: float,
    ) -> list[Place]:
        """Fetch and parse one Overpass endpoint."""
        timeout = aiohttp.ClientTimeout(total=75)
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "Referer": PROJECT_URL,
        }
        async with session.post(
            endpoint,
            data={"data": query},
            headers=headers,
            timeout=timeout,
        ) as response:
            response.raise_for_status()
            payload = await response.json(content_type=None)

        elements = payload.get("elements")
        if not isinstance(elements, list):
            raise ValueError("Overpass response did not contain an elements list")

        places_by_id: dict[str, Place] = {}

        for element in elements:
            if not isinstance(element, dict):
                continue

            lat_lon = _extract_coordinates(element)
            if lat_lon is None:
                continue
            latitude, longitude = lat_lon

            distance_m = distance(
                home_latitude,
                home_longitude,
                latitude,
                longitude,
            )
            if distance_m is None:
                continue

            distance_km = distance_m / 1000
            if distance_km > self.radius_km + 0.05:
                continue

            tags = {
                str(k): str(v)
                for k, v in dict(element.get("tags", {})).items()
                if v is not None
            }
            osm_type = str(element.get("type", "node"))
            try:
                osm_id = int(element["id"])
            except (KeyError, TypeError, ValueError):
                continue

            for category in self._categories_for(tags):
                unique_id = f"{category}:{osm_type}:{osm_id}"
                name = _display_name(tags, category, osm_id)
                places_by_id[unique_id] = Place(
                    unique_id=unique_id,
                    osm_type=osm_type,
                    osm_id=osm_id,
                    category=category,
                    name=name,
                    latitude=latitude,
                    longitude=longitude,
                    distance_km=round(distance_km, 3),
                    tags=tags,
                )

        return sorted(
            places_by_id.values(),
            key=lambda item: (item.category, item.distance_km, item.name.casefold()),
        )

    def _categories_for(self, tags: dict[str, str]) -> set[str]:
        """Return all categories represented by an active OSM feature."""
        categories: set[str] = set()

        if not _is_active_feature(tags):
            return categories

        if (
            self._enabled(CONF_FIRE_STATIONS, DEFAULT_FIRE_STATIONS)
            and tags.get("amenity") == "fire_station"
        ):
            categories.add(CATEGORY_FIRE_STATION)

        if self._enabled(CONF_HOSPITALS, DEFAULT_HOSPITALS) and (
            tags.get("amenity") == "hospital"
            or tags.get("healthcare") == "hospital"
        ):
            categories.add(CATEGORY_HOSPITAL)

        if (
            self._enabled(
                CONF_AMBULANCE_STATIONS,
                DEFAULT_AMBULANCE_STATIONS,
            )
            and (
                tags.get("emergency") == "ambulance_station"
                or tags.get("amenity") == "ambulance_station"
            )
            and _is_rettungswache(tags)
        ):
            categories.add(CATEGORY_AMBULANCE_STATION)

        return categories

    def _build_query(
        self,
        radius_m: int,
        latitude: float,
        longitude: float,
    ) -> str:
        """Build a compact Overpass query for the enabled categories."""
        around = f"(around:{radius_m},{latitude:.6f},{longitude:.6f})"
        statements: list[str] = []

        if self._enabled(CONF_FIRE_STATIONS, DEFAULT_FIRE_STATIONS):
            statements.append(f'nwr{around}["amenity"="fire_station"];')

        if self._enabled(CONF_HOSPITALS, DEFAULT_HOSPITALS):
            statements.extend(
                (
                    f'nwr{around}["amenity"="hospital"];',
                    f'nwr{around}["healthcare"="hospital"];',
                )
            )

        if self._enabled(
            CONF_AMBULANCE_STATIONS,
            DEFAULT_AMBULANCE_STATIONS,
        ):
            statements.extend(
                (
                    f'nwr{around}["emergency"="ambulance_station"];',
                    f'nwr{around}["amenity"="ambulance_station"];',
                )
            )

        body = "\n".join(statements)
        return f"""[out:json][timeout:60];
(
{body}
);
out center tags;
"""


def _extract_coordinates(element: dict[str, Any]) -> tuple[float, float] | None:
    """Extract coordinates from an OSM node, way or relation."""
    lat = element.get("lat")
    lon = element.get("lon")

    if lat is None or lon is None:
        center = element.get("center")
        if isinstance(center, dict):
            lat = center.get("lat")
            lon = center.get("lon")

    try:
        return float(lat), float(lon)
    except (TypeError, ValueError):
        return None


def _is_active_feature(tags: dict[str, str]) -> bool:
    """Return False for lifecycle-tagged or explicitly inactive OSM features."""
    inactive_values = {
        "abandoned",
        "closed",
        "demolished",
        "destroyed",
        "disused",
        "former",
        "historic",
        "no",
        "razed",
        "removed",
    }

    for key in (
        "abandoned",
        "demolished",
        "destroyed",
        "disused",
        "razed",
        "removed",
    ):
        if tags.get(key, "").strip().lower() in {"yes", "true", "1"}:
            return False

    if tags.get("operational_status", "").strip().lower() in inactive_values:
        return False
    if tags.get("status", "").strip().lower() in inactive_values:
        return False

    lifecycle_prefixes = (
        "abandoned:",
        "demolished:",
        "destroyed:",
        "disused:",
        "former:",
        "razed:",
        "removed:",
    )
    if any(key.startswith(lifecycle_prefixes) for key in tags):
        return False

    return True


def _is_rettungswache(tags: dict[str, str]) -> bool:
    """Keep emergency Rettungswachen, not generic private ambulance businesses."""
    fields = (
        tags.get("name", ""),
        tags.get("official_name", ""),
        tags.get("operator", ""),
        tags.get("brand", ""),
        tags.get("description", ""),
    )
    text = " " + " ".join(fields).casefold() + " "

    if any(term in text for term in _RETTUNGSWACHE_TERMS):
        return True

    if any(term in text for term in _RECOGNIZED_RESCUE_ORGS):
        return True

    operator_type = tags.get("operator:type", "").strip().casefold()
    if operator_type in {
        "government",
        "public",
        "community",
        "religious",
        "ngo",
        "nonprofit",
        "non_profit",
    }:
        return True

    return False


def _display_name(
    tags: dict[str, str],
    category: str,
    osm_id: int,
) -> str:
    """Return the best available display name."""
    if name := (
        tags.get("name")
        or tags.get("operator")
        or tags.get("brand")
        or tags.get("official_name")
    ):
        return name

    fallback = {
        CATEGORY_FIRE_STATION: "Fire station",
        CATEGORY_HOSPITAL: "Hospital",
        CATEGORY_AMBULANCE_STATION: "Rettungswache",
    }[category]
    return f"{fallback} (OSM {osm_id})"
