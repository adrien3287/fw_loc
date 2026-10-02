# FW Locations

HACS custom integration for Home Assistant that creates `geo_location` entities for nearby emergency and healthcare infrastructure using OpenStreetMap/Overpass.

## Locations

- Fire stations / Feuerwachen — `mdi:fire`
- Hospitals — `mdi:hospital-marker`
- Ambulance stations / Rettungswachen — `mdi:ambulance`
- General practitioners / Hausärzte — `mdi:plus-circle`

The search is centered on the **Home Assistant Home coordinates** and is hard-limited to **50 km**. No home address or fixed coordinates are stored in the repository.

## Data source

The integration queries OpenStreetMap through public Overpass API endpoints every 6 hours. Results are cached locally in Home Assistant. If Overpass is temporarily unavailable, the most recently cached dataset is reused.

OpenStreetMap coverage varies. In particular, doctor specialties are not always tagged. Practices without an explicit specialty are kept; practices explicitly tagged only with a non-general specialty are excluded.

## Installation with HACS

1. In HACS, open **Integrations**.
2. Add `https://github.com/adrien3287/fw_loc` as a **Custom repository** of type **Integration**.
3. Install **FW Locations**.
4. Restart Home Assistant.
5. Go to **Settings → Devices & services → Add integration**.
6. Search for **FW Locations**.
7. Choose a radius from 1 to 50 km and the desired categories.

## Home Assistant map

All entities use the source `fw_loc`, so a map card can display them together:

```yaml
type: map
geo_location_sources:
  - fw_loc
```

Each entity exposes latitude, longitude, distance from Home, category, OSM object information and common metadata such as operator, address, phone, website and opening hours when available.

## OSM tags queried

- `amenity=fire_station`
- `building=fire_station`
- `amenity=hospital`
- `healthcare=hospital`
- `emergency=ambulance_station`
- legacy `amenity=ambulance_station`
- `amenity=doctors`
- `healthcare=doctor`

## Notes on marker colors

The integration exposes a `marker_color` attribute for each category, but the standard Home Assistant map currently controls marker rendering. The icon shapes are therefore the reliable category distinction in the stock map.

## License

MIT
