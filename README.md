# FW Locations

HACS custom integration for Home Assistant that creates `geo_location` entities for nearby emergency infrastructure using OpenStreetMap/Overpass.

## Locations

- Active fire stations / Feuerwachen — `mdi:fire`
- Hospitals — `mdi:hospital-marker`
- Rettungswachen / emergency rescue stations — `mdi:ambulance`

The search is centered on the **Home Assistant Home coordinates** and is hard-limited to **50 km**. No home address or fixed coordinates are stored in the repository.

## Filtering

FW Locations intentionally favors operational emergency infrastructure over broad POI coverage.

### Fire stations

Only objects tagged `amenity=fire_station` are used. A building that merely keeps `building=fire_station` after the fire service has moved out is not included.

Objects carrying lifecycle/status tags such as `disused:*`, `abandoned:*`, `demolished:*`, `removed:*`, `status=closed`, etc. are excluded.

### Rettungswachen

OpenStreetMap's `emergency=ambulance_station` can describe both emergency Rettungswachen and private ambulance businesses. FW Locations therefore applies an additional filter and keeps only entries that look like actual Rettungsdienst / Notfallrettung stations, based on station naming, recognized emergency-service operators, or public/non-profit operator classification.

Generic private ambulance / patient transport businesses without Rettungswache or Rettungsdienst evidence are excluded.

### Doctors

Doctors and general practitioners are deliberately **not included**.

## Data source

The integration queries OpenStreetMap through several public Overpass API endpoints every 6 hours. Results are cached locally in Home Assistant. If Overpass is temporarily unavailable, the most recently cached valid dataset is reused.

## Installation with HACS

1. In HACS, open **Integrations**.
2. Add `https://github.com/adrien3287/fw_loc` as a **Custom repository** of type **Integration**.
3. Install **FW Locations**.
4. Restart Home Assistant.
5. Go to **Settings → Devices & services → Add integration**.
6. Search for **FW Locations**.
7. Choose a radius from 1 to 50 km and the desired categories.

## Home Assistant map

All entities use the source `fw_loc`. Use `label_mode: icon` so Home Assistant renders the entity MDI icon instead of initials from the friendly name:

```yaml
type: map
geo_location_sources:
  - source: fw_loc
    label_mode: icon
```

Each entity exposes latitude, longitude, distance from Home, category, OSM object information and common metadata such as operator, address, phone, website and opening hours when available.

Entities that disappear from the filtered feed are removed dynamically from Home Assistant.

## OSM tags queried

- `amenity=fire_station`
- `amenity=hospital`
- `healthcare=hospital`
- `emergency=ambulance_station`
- legacy `amenity=ambulance_station`

## Notes on marker colors

The integration exposes a `marker_color` attribute for each category, but the standard Home Assistant map currently controls marker rendering. The icon shapes are therefore the reliable category distinction in the stock map.

## License

MIT
