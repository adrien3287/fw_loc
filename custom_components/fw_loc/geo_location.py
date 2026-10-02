"""Geolocation entities for FW Locations."""

from __future__ import annotations

from typing import Any

from homeassistant.components.geo_location import GeolocationEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfLength
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CATEGORY_AMBULANCE_STATION,
    CATEGORY_FIRE_STATION,
    CATEGORY_HOSPITAL,
    DOMAIN,
    SOURCE,
)
from .coordinator import FwLocCoordinator, Place

ICONS = {
    CATEGORY_FIRE_STATION: "mdi:fire-station",
    CATEGORY_HOSPITAL: "mdi:hospital-building",
    CATEGORY_AMBULANCE_STATION: "mdi:ambulance",
}

MARKER_COLORS = {
    CATEGORY_FIRE_STATION: "#e53935",
    CATEGORY_HOSPITAL: "#1565c0",
    CATEGORY_AMBULANCE_STATION: "#d32f2f",
}

CATEGORY_LABELS = {
    CATEGORY_FIRE_STATION: "Fire station",
    CATEGORY_HOSPITAL: "Hospital",
    CATEGORY_AMBULANCE_STATION: "Rettungswache",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up FW Locations geolocation entities."""
    coordinator: FwLocCoordinator = entry.runtime_data
    entities: dict[str, FwLocGeolocationEntity] = {}
    entity_registry = er.async_get(hass)

    @callback
    def _sync_entities() -> None:
        """Add new locations and remove locations no longer in the feed."""
        places = coordinator.data or []
        places_by_id = {place.unique_id: place for place in places}
        current_ids = set(places_by_id)
        known_ids = set(entities)
        valid_unique_ids = {
            f"{DOMAIN}_{place_id.replace(':', '_')}" for place_id in current_ids
        }

        # Clean up registry entries from removed categories or filtered-out POIs.
        registry_ids_to_remove = [
            registry_entry.entity_id
            for registry_entry in entity_registry.entities.values()
            if registry_entry.config_entry_id == entry.entry_id
            and registry_entry.unique_id.startswith(f"{DOMAIN}_")
            and registry_entry.unique_id not in valid_unique_ids
        ]
        for entity_id in registry_ids_to_remove:
            entity_registry.async_remove(entity_id)

        for stale_id in known_ids - current_ids:
            stale_entity = entities.pop(stale_id)
            hass.async_create_task(stale_entity.async_remove(force_remove=True))

        new_places = [
            places_by_id[place_id]
            for place_id in current_ids - known_ids
        ]
        if not new_places:
            return

        new_entities = [
            FwLocGeolocationEntity(coordinator, place)
            for place in new_places
        ]
        for entity in new_entities:
            entities[entity.place_id] = entity

        async_add_entities(new_entities)

    _sync_entities()
    entry.async_on_unload(coordinator.async_add_listener(_sync_entities))


class FwLocGeolocationEntity(
    CoordinatorEntity[FwLocCoordinator],
    GeolocationEvent,
):
    """A nearby emergency or healthcare location."""

    _attr_should_poll = False
    _attr_source = SOURCE
    _attr_unit_of_measurement = UnitOfLength.KILOMETERS

    def __init__(self, coordinator: FwLocCoordinator, place: Place) -> None:
        """Initialize a geolocation entity."""
        CoordinatorEntity.__init__(self, coordinator)
        self._place_id = place.unique_id
        self._attr_unique_id = f"{DOMAIN}_{place.unique_id.replace(':', '_')}"
        self._attr_name = place.name
        self._attr_icon = ICONS[place.category]

    @property
    def place_id(self) -> str:
        """Return the internal place identifier."""
        return self._place_id

    @property
    def _place(self) -> Place | None:
        """Return the current place from coordinator data."""
        if not self.coordinator.data:
            return None
        return next(
            (
                place
                for place in self.coordinator.data
                if place.unique_id == self._place_id
            ),
            None,
        )

    @property
    def available(self) -> bool:
        """Return entity availability."""
        return super().available and self._place is not None

    @property
    def distance(self) -> float | None:
        """Return distance from Home Assistant home coordinates in km."""
        if (place := self._place) is None:
            return None
        return place.distance_km

    @property
    def latitude(self) -> float | None:
        """Return latitude."""
        if (place := self._place) is None:
            return None
        return place.latitude

    @property
    def longitude(self) -> float | None:
        """Return longitude."""
        if (place := self._place) is None:
            return None
        return place.longitude

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return useful OSM and category metadata."""
        if (place := self._place) is None:
            return {}

        tags = place.tags
        attributes: dict[str, Any] = {
            "category": place.category,
            "category_name": CATEGORY_LABELS[place.category],
            "marker_color": MARKER_COLORS[place.category],
            "data_source": "OpenStreetMap / Overpass",
            "data_cached": self.coordinator.using_cache,
            "data_updated_at": self.coordinator.data_updated_at,
            "osm_type": place.osm_type,
            "osm_id": place.osm_id,
            "osm_url": f"https://www.openstreetmap.org/{place.osm_type}/{place.osm_id}",
            "distance_km": place.distance_km,
        }

        for key in (
            "operator",
            "operator:type",
            "brand",
            "ref",
            "addr:street",
            "addr:housenumber",
            "addr:postcode",
            "addr:city",
            "phone",
            "contact:phone",
            "website",
            "contact:website",
            "opening_hours",
            "emergency",
            "healthcare",
        ):
            if key in tags:
                attributes[key.replace(":", "_")] = tags[key]

        return attributes
