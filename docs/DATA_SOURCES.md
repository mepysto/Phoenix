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
| **NASA LANCE FIRMS** | Active fires, VIIRS S-NPP + NOAA-20 (375 m), last 24–48 h | NASA open data | ✅ | Credit "NASA LANCE FIRMS" and follow the [LANCE citation & disclaimer](https://www.earthdata.nasa.gov/data/tools/firms/faq) when redistributing. Keyless 24 h global files, ingested into PostGIS every 30 min | 30 min |
| **USGS ShakeMap** | Shaking-intensity contours (MMI IV+) of the past week's M4.5+ earthquakes | U.S. Government public domain | ✅ | "Shaking intensity: USGS ShakeMap"; aggregated and cached by the API | 10 min |
| **NASA GIBS** — VIIRS SNPP Day/Night Band | Night lights (power-outage indicator) | NASA open data (no restrictions) | ✅ | "Imagery © NASA GIBS / ESDIS" | Daily |

## Infrastructure (reference data)

Imported into PostGIS by `python -m scripts.import_infrastructure` and served
per map viewport (`GET /api/v1/infrastructure`), most significant first.

| Source | Layer | Licence | Commercial | Attribution / conditions | Updated |
|---|---|---|---|---|---|
| **WRI Global Power Plant Database** v1.3 | ~35,000 power plants (capacity, fuel) | CC BY 4.0 | ✅ | "Power plants: WRI Global Power Plant Database (CC BY 4.0)". Frozen since 2021. | Static |
| **Global Dam Watch** v1 (EU JRC open-data mirror) | ~41,000 dams (height, reservoir, use) | CC BY 4.0, © European Union | ✅ | "Dams: Global Dam Watch (CC BY 4.0)"; reuse must credit the source and indicate changes | Static |
| **OpenStreetMap (via OpenFreeMap)** | Hospitals (zoom 14+; OpenMapTiles omits them at lower zooms) | ODbL | ✅ | "© OpenStreetMap contributors" (drawn from the basemap's vector tiles; no extra requests) | Weekly |

The public Overpass API was not used: its policy says public instances must
not be relied on as the backend of a public website.

## Monitoring

Moving objects relevant to a response, computed or relayed by the API (`/api/v1/tracks/*`).

| Source | Layer | Licence | Commercial | Attribution / conditions | Refresh |
|---|---|---|---|---|---|
| **CelesTrak** (GP element sets, "Earth resources" group) | Earth-observation satellite positions and passes over an event (Sentinel, Landsat, WorldView, …), propagated with SGP4 | No explicit licence published; data originates from the US Space Force (18 SDS) | ❌ unconfirmed — non-commercial deployments only until verified | "Satellite orbits: CelesTrak". [Usage policy](https://celestrak.org/usage-policy.php): download each update at most once (we cache 6 h) and stop querying after errors (we pause 1 h) | 6 h orbits, 30 s positions |
| **adsb.lol** (ADS-B aggregator) | Aircraft around the view (zoom 5+): callsign, type, altitude, speed, heading; military highlighted | ODbL | ✅ | "Aircraft: adsb.lol (ODbL)"; derived databases must stay ODbL. Keyless for now (maintainer asks production users to get in touch). Proxied and cached 10 s per ~50 km cell. **Aircraft in the FAA PIA/LADD privacy programmes are excluded.** | 15 s |
| **AISStream** (WebSocket) | Ships around active high/critical events (zoom 4+): name, type, speed, course/heading | AISStream terms; no explicit licence | ❌ unconfirmed | "Ships: AISStream". **Needs a free key** (`AISSTREAM_API_KEY`, server-side only: the terms forbid browser connections). One stream per deployment (3 connections per account), subscribed only to boxes around severe events; positions kept 2 h | Live (served 15 s) |
| **Caltrans** CCTV (California DOT, CWWP2) | ~3,400 public highway cameras: location, direction, latest still image (via the API proxy) | Public domain ("information presented on this website … is considered in the public domain") | ✅ | "Cameras: Caltrans". Free for integration over HTTPS; images are not retained upstream and Phoenix does not archive them. Camera list cached 1 h, snapshots 60 s | Images every ~5 min |
| **Radio Browser** (community directory) | Local radio stations near an event (event card): stream, language, and whether the station passed its last health check (off air = possible outage) | "Completely free and open source; may be used in free and non-free software" | ✅ | Identifying User-Agent required. Searches proxied and cached 1 h per ~10 km cell; audio is streamed by the browser directly from the station (only https streams play in-page) | On request |

## Removed sources

| Source | Why |
|---|---|
| CARTO basemaps | Began rendering an "API KEY REQUIRED" watermark. |
| Esri World Imagery / World Dark Gray | Terms could not be confirmed to allow use without an ArcGIS licence. |

