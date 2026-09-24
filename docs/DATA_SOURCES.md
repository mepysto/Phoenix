# Data Sources

Every dataset Phoenix displays, with its licence, attribution and whether a
**commercial** deployment may use it. Licence terms were checked against each
provider's own terms (September 2026); re-check before relying on them.

Phoenix is operated **non-commercially** (humanitarian / NGO). Sources marked
*non-commercial only* are switched off automatically when a deployment sets
`NEXT_PUBLIC_COMMERCIAL_DEPLOYMENT=1`.

**Adding a source:** verify its licence on the provider's site (not from
memory), add a row here, and set `commercialUse` in
`apps/web/src/lib/layers/registry.ts` (overlays) or `lib/map/basemaps.ts`.
A unit test fails if a registry source is missing from this file.

## Event feeds (ingested by the API)

| Source | Data | Licence | Commercial | Attribution / conditions | Refresh |
|---|---|---|---|---|---|
| **GDACS** (Global Disaster Alert and Coordination System) | Disaster alerts (EQ, TC, FL, VO, DR, WF) | CC BY 4.0 | ✅ | "Global Disaster Alert and Coordination System, GDACS". GDACS information "is purely indicative and should not be used for any decision making without alternate sources of information". | 5 min |
| **USGS** Earthquake Hazards Program | M4.5+ earthquakes (GeoJSON feed) | U.S. Government public domain | ✅ | Credit "U.S. Geological Survey" requested | 5 min |
| **NASA EONET** | Natural events (wildfires, storms, volcanoes…) | NASA open data (no restrictions) | ✅ | Credit "NASA EONET" requested | 10 min |
| **Copernicus EMS** Rapid Mapping | Emergency mapping activations (EMSR) | CC BY 4.0 | ✅ | "© European Union, Copernicus Emergency Management Service"; indicate changes | 5 min |

## Basemaps

| Source | Used for | Licence | Commercial | Attribution |
|---|---|---|---|---|
| **OpenFreeMap** (OpenMapTiles schema) | Dark vector basemap, labels, fonts | OpenFreeMap: MIT; data © OpenStreetMap contributors (ODbL) | ✅ | "OpenFreeMap © OpenMapTiles Data from OpenStreetMap" (shown automatically) |
| **EOxCloudless** — Sentinel-2 cloudless 2025 | Satellite basemap (10 m) | CC BY-NC-SA 4.0 | ❌ non-commercial only (NGOs allowed; commercial needs an EOX licence) | "EOxCloudless https://cloudless.eox.at by EOX IT Services GmbH (Contains modified Copernicus Sentinel data 2025)" |
| **NASA Blue Marble** (via GIBS) | Satellite basemap in commercial deployments (~500 m) | NASA open data | ✅ | "Imagery © NASA Blue Marble (GIBS)" |

## Map overlays (layer registry)

| Source | Layer | Licence | Commercial | Attribution / conditions | Refresh |
|---|---|---|---|---|---|
| **RainViewer** | Precipitation radar | "Personal and educational use only" | ❌ non-commercial only | Must link to https://www.rainviewer.com/ as the data source. Radar availability is not guaranteed. | 10 min |
| **NASA GIBS** — GOES-East ABI Band 13 | Infrared clouds | NASA open data (no restrictions) | ✅ | "Imagery © NASA GIBS / ESDIS" | 10 min |
| **NOAA National Hurricane Center** | Tropical cyclones: forecast cone, track, positions, past track (Atlantic, East & Central Pacific) | U.S. Government public domain | ✅ | "Tropical cyclones: NOAA NHC"; aggregated and cached by the API | 10 min |
| **USGS ShakeMap** | Shaking-intensity contours (MMI IV+) of the past week's M4.5+ earthquakes | U.S. Government public domain | ✅ | "Shaking intensity: USGS ShakeMap"; aggregated and cached by the API | 10 min |
| **NASA GIBS** — VIIRS SNPP Day/Night Band | Night lights (power-outage indicator) | NASA open data (no restrictions) | ✅ | "Imagery © NASA GIBS / ESDIS" | Daily |

## Removed sources

| Source | Why |
|---|---|
| CARTO basemaps | Began rendering an "API KEY REQUIRED" watermark. |
| Esri World Imagery / World Dark Gray | Terms could not be confirmed to allow use without an ArcGIS licence. |

## Planned (not yet integrated)

| Source | Needs | Notes |
|---|---|---|
| NASA FIRMS active fires | Free `FIRMS_MAP_KEY` (server-side only) | Will be served through the API; the key is never sent to browsers. |
