/**
 * Map overlay layer registry (G-1).
 *
 * Every overlay declares where its data comes from, its licence, whether it
 * needs an API key (GEV model: keyless layers always work, keys only unlock
 * more), and how to resolve its current tiles. The map, the layer panel and
 * the data-source attribution are all driven from this list.
 */

import type { ExpressionSpecification, LayerSpecification } from "maplibre-gl";
import { API_URL } from "@/lib/api/client";
import { COMMERCIAL_DEPLOYMENT, LABEL_FONT } from "@/lib/map/basemaps";
import { bboxCenter, bboxRadiusKm } from "@/lib/map/geo";

export type LayerCategory = "weather" | "satellite" | "hazards" | "infrastructure" | "monitoring";

/** keyless: works for everyone; free_key/metered: needs a server-side key */
export type LayerAuth = "keyless" | "free_key" | "metered";

export interface LayerSourceInfo {
  name: string;
  url: string;
  license: string;
  /** May a commercial deployment use it? (verified from the provider's terms) */
  commercialUse: boolean;
  /** Shown in the map's attribution control (may contain HTML) */
  attribution: string;
}

export interface ResolvedTiles {
  tiles: string[];
  maxzoom: number;
  tileSize?: number;
}

export interface RasterLayerDefinition {
  id: string;
  kind: "raster";
  category: LayerCategory;
  auth: LayerAuth;
  source: LayerSourceInfo;
  defaultOpacity: number;
  /** Re-resolve tiles this often while visible (live data) */
  refreshMs?: number;
  /** Current tile URL templates; may fetch metadata (e.g. latest radar frame) */
  resolveTiles: (now: Date) => Promise<ResolvedTiles>;
}

/** What the map currently shows, for viewport-driven layers */
export interface Viewport {
  /** [west, south, east, north]; west > east when crossing the antimeridian */
  bbox: [number, number, number, number];
  zoom: number;
}

export interface GeoJsonLayerDefinition {
  id: string;
  kind: "geojson";
  category: LayerCategory;
  auth: LayerAuth;
  source: LayerSourceInfo;
  defaultOpacity: number;
  refreshMs?: number;
  /** Re-query when the map moves (large datasets served per viewport) */
  viewportDriven?: boolean;
  /** Below this zoom the layer shows nothing (too many features) */
  minZoom?: number;
  loadData: (viewport: Viewport) => Promise<GeoJSON.FeatureCollection>;
  /** MapLibre layers drawing the source, bottom to top */
  styleLayers: (sourceId: string) => LayerSpecification[];
}

/** Restyles data the basemap already loads (no extra requests) */
export interface StyleLayerDefinition {
  id: string;
  kind: "style";
  category: LayerCategory;
  auth: LayerAuth;
  source: LayerSourceInfo;
  defaultOpacity: number;
  /** Source id in the basemap style */
  basemapSource: string;
  styleLayers: (sourceId: string) => LayerSpecification[];
}

export type LayerDefinition =
  | RasterLayerDefinition
  | GeoJsonLayerDefinition
  | StyleLayerDefinition;

/** Saffir-Simpson colours (TD/TS, then categories 1-5) */
const SSHS_COLOR: unknown[] = [
  "match",
  ["coalesce", ["get", "saffir_simpson"], 0],
  1, "#ffffcc",
  2, "#ffe775",
  3, "#ffc140",
  4, "#ff8f20",
  5, "#ff6060",
  /* TS/TD */ "#5ebaff",
];
const kind = (value: string) => ["==", ["get", "kind"], value];
const currentPosition = ["all", kind("position"), ["==", ["coalesce", ["get", "tau_hours"], 0], 0]];

function cycloneStyleLayers(sourceId: string): LayerSpecification[] {
  return [
    {
      id: `${sourceId}-cone`,
      type: "fill",
      source: sourceId,
      filter: kind("cone"),
      paint: { "fill-color": "#ffffff", "fill-opacity": 0.12 },
    },
    {
      id: `${sourceId}-cone-outline`,
      type: "line",
      source: sourceId,
      filter: kind("cone"),
      paint: { "line-color": "#ffffff", "line-opacity": 0.6, "line-width": 1 },
    },
    {
      id: `${sourceId}-past`,
      type: "line",
      source: sourceId,
      filter: kind("past_track"),
      paint: { "line-color": "#9ca3af", "line-width": 1.5, "line-dasharray": [2, 2] },
    },
    {
      id: `${sourceId}-track`,
      type: "line",
      source: sourceId,
      filter: kind("track"),
      paint: { "line-color": "#ffffff", "line-width": 2 },
    },
    {
      id: `${sourceId}-points`,
      type: "circle",
      source: sourceId,
      filter: kind("position"),
      paint: {
        "circle-color": SSHS_COLOR,
        "circle-radius": ["case", currentPosition, 8, 4],
        "circle-stroke-color": "#111827",
        "circle-stroke-width": 1,
      },
    },
    {
      id: `${sourceId}-label`,
      type: "symbol",
      source: sourceId,
      filter: currentPosition,
      layout: {
        "text-field": [
          "concat",
          ["get", "storm_name"],
          [
            "case",
            [">", ["coalesce", ["get", "saffir_simpson"], 0], 0],
            ["concat", " · Cat ", ["to-string", ["get", "saffir_simpson"]]],
            "",
          ],
          ["case", ["has", "max_wind_kt"], ["concat", " · ", ["to-string", ["get", "max_wind_kt"]], " kt"], ""],
        ],
        "text-font": LABEL_FONT,
        "text-size": 12,
        "text-offset": [0, 1.4],
        "text-anchor": "top",
      },
      paint: { "text-color": "#ffffff", "text-halo-color": "#111827", "text-halo-width": 1.5 },
    },
  ] as LayerSpecification[];
}

const MMI_ROMAN: unknown[] = [
  "match",
  ["get", "mmi"],
  4, "IV", 5, "V", 6, "VI", 7, "VII", 8, "VIII", 9, "IX", 10, "X",
  "",
];

function shakemapStyleLayers(sourceId: string): LayerSpecification[] {
  return [
    {
      id: `${sourceId}-contours`,
      type: "line",
      source: sourceId,
      layout: { "line-join": "round", "line-cap": "round" },
      paint: {
        // USGS's own intensity palette, carried on each contour
        "line-color": ["coalesce", ["get", "color"], "#ffff00"],
        "line-width": ["interpolate", ["linear"], ["get", "mmi"], 4, 1, 8, 4],
      },
    },
    {
      id: `${sourceId}-labels`,
      type: "symbol",
      source: sourceId,
      // Label whole-intensity contours only (4.5, 5.5 ... are unlabelled)
      filter: ["==", ["%", ["get", "mmi"], 1], 0],
      layout: {
        "symbol-placement": "line",
        "text-field": ["concat", "MMI ", MMI_ROMAN],
        "text-font": LABEL_FONT,
        "text-size": 11,
      },
      paint: { "text-color": "#ffffff", "text-halo-color": "#111827", "text-halo-width": 1.5 },
    },
  ] as LayerSpecification[];
}

/** Viewport query against the infrastructure API */
async function loadInfrastructure(kind: "dam" | "power_plant", viewport: Viewport) {
  const [west, south, east, north] = viewport.bbox;
  const params = new URLSearchParams({
    min_lng: String(west),
    min_lat: String(south),
    max_lng: String(east),
    max_lat: String(north),
    kinds: kind,
    limit: "2000",
  });
  const response = await fetch(`${API_URL}/api/v1/infrastructure?${params}`);
  if (!response.ok) throw new Error(`Infrastructure ${response.status}`);
  return (await response.json()) as GeoJSON.FeatureCollection;
}

const INFRASTRUCTURE_LABEL = (sourceId: string, minzoom: number): LayerSpecification => ({
  id: `${sourceId}-labels`,
  type: "symbol",
  source: sourceId,
  minzoom,
  layout: {
    "text-field": ["coalesce", ["get", "name"], ""],
    "text-font": LABEL_FONT,
    "text-size": 11,
    "text-offset": [0, 1.1],
    "text-anchor": "top",
    "text-optional": true,
  },
  paint: { "text-color": "#e5e7eb", "text-halo-color": "#111827", "text-halo-width": 1.2 },
});

/** WRI primary_fuel -> colour */
const FUEL_COLOR: ExpressionSpecification = [
  "match",
  ["get", "primary_fuel"],
  "Hydro", "#3b82f6",
  "Nuclear", "#a855f7",
  "Coal", "#6b7280",
  "Gas", "#f97316",
  "Oil", "#92400e",
  "Solar", "#facc15",
  "Wind", "#2dd4bf",
  "Biomass", "#65a30d",
  "Geothermal", "#dc2626",
  "#9ca3af",
];

const GIBS = "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best";
const GIBS_SOURCE = {
  name: "NASA GIBS",
  url: "https://www.earthdata.nasa.gov/engage/open-data-services-software/earthdata-developer-portal/gibs-api",
  license: "NASA open data (no restrictions)",
  commercialUse: true,
  attribution: "Imagery &copy; NASA GIBS / ESDIS",
};

/** Cache-buster rounded to `ms`, so tiles refresh on schedule but still cache */
const bucket = (now: Date, ms: number) => Math.floor(now.getTime() / ms);

const TEN_MINUTES = 10 * 60_000;

const ALL_LAYER_DEFINITIONS: LayerDefinition[] = [
  {
    id: "radar",
    kind: "raster",
    category: "weather",
    auth: "keyless",
    source: {
      name: "RainViewer",
      url: "https://www.rainviewer.com/api.html",
      // "This API is available for personal and educational use only" and
      // asks for a link to rainviewer.com as the data source
      license: "Personal and educational use only; link attribution required",
      commercialUse: false,
      attribution: 'Radar &copy; <a href="https://www.rainviewer.com/">RainViewer</a>',
    },
    defaultOpacity: 0.7,
    refreshMs: TEN_MINUTES,
    resolveTiles: async () => {
      // The newest radar frame changes every ~10 minutes
      const response = await fetch("https://api.rainviewer.com/public/weather-maps.json");
      if (!response.ok) throw new Error(`RainViewer ${response.status}`);
      const maps = (await response.json()) as {
        host: string;
        radar: { past: { path: string }[] };
      };
      const latest = maps.radar.past.at(-1);
      if (!latest) throw new Error("RainViewer returned no radar frames");
      // Color scheme 2 (universal blue), smoothed, with snow shown
      return {
        tiles: [`${maps.host}${latest.path}/256/{z}/{x}/{y}/2/1_1.png`],
        maxzoom: 7,
      };
    },
  },
  {
    id: "clouds-infrared",
    kind: "raster",
    category: "satellite",
    auth: "keyless",
    source: { ...GIBS_SOURCE, name: "NASA GIBS — GOES-East ABI Band 13" },
    defaultOpacity: 0.6,
    refreshMs: TEN_MINUTES,
    resolveTiles: async (now) => ({
      tiles: [
        `${GIBS}/GOES-East_ABI_Band13_Clean_Infrared/default/default/GoogleMapsCompatible_Level6/{z}/{y}/{x}.png?v=${bucket(now, TEN_MINUTES)}`,
      ],
      maxzoom: 6,
    }),
  },
  {
    id: "night-lights",
    kind: "raster",
    category: "satellite",
    auth: "keyless",
    // Daily night-time radiance: sudden dark areas indicate power outages
    source: { ...GIBS_SOURCE, name: "NASA GIBS — VIIRS SNPP Day/Night Band" },
    defaultOpacity: 0.8,
    resolveTiles: async () => ({
      tiles: [
        `${GIBS}/VIIRS_SNPP_DayNightBand_At_Sensor_Radiance/default/default/GoogleMapsCompatible_Level8/{z}/{y}/{x}.png`,
      ],
      maxzoom: 8,
    }),
  },
  {
    id: "cyclones",
    kind: "geojson",
    category: "hazards",
    auth: "keyless",
    source: {
      name: "NOAA National Hurricane Center",
      url: "https://www.nhc.noaa.gov/gis/",
      license: "U.S. Government public domain",
      commercialUse: true,
      attribution: "Tropical cyclones: NOAA NHC",
    },
    defaultOpacity: 1,
    refreshMs: TEN_MINUTES,
    loadData: async () => {
      // Aggregated and cached by the API (NHC splits storms across 15 layers)
      const response = await fetch(`${API_URL}/api/v1/hazards/cyclones`);
      if (!response.ok) throw new Error(`Cyclones ${response.status}`);
      return (await response.json()) as GeoJSON.FeatureCollection;
    },
    styleLayers: cycloneStyleLayers,
  },
  {
    id: "shakemaps",
    kind: "geojson",
    category: "hazards",
    auth: "keyless",
    source: {
      name: "USGS ShakeMap",
      url: "https://earthquake.usgs.gov/data/shakemap/",
      license: "U.S. Government public domain",
      commercialUse: true,
      attribution: "Shaking intensity: USGS ShakeMap",
    },
    defaultOpacity: 0.9,
    refreshMs: TEN_MINUTES,
    loadData: async () => {
      const response = await fetch(`${API_URL}/api/v1/hazards/shakemaps`);
      if (!response.ok) throw new Error(`ShakeMaps ${response.status}`);
      return (await response.json()) as GeoJSON.FeatureCollection;
    },
    styleLayers: shakemapStyleLayers,
  },
  {
    id: "fires",
    kind: "geojson",
    category: "hazards",
    auth: "keyless",
    source: {
      name: "NASA LANCE FIRMS",
      url: "https://www.earthdata.nasa.gov/data/tools/firms",
      license: "NASA open data; LANCE citation and disclaimer apply",
      commercialUse: true,
      attribution:
        'Active fires: <a href="https://www.earthdata.nasa.gov/data/tools/firms">NASA LANCE FIRMS</a>',
    },
    defaultOpacity: 0.9,
    refreshMs: TEN_MINUTES * 3,
    viewportDriven: true,
    minZoom: 1,
    loadData: async ({ bbox: [west, south, east, north] }) => {
      const params = new URLSearchParams({
        min_lng: String(west),
        min_lat: String(south),
        max_lng: String(east),
        max_lat: String(north),
        limit: "3000",
      });
      const response = await fetch(`${API_URL}/api/v1/hazards/fires?${params}`);
      if (!response.ok) throw new Error(`Fires ${response.status}`);
      return (await response.json()) as GeoJSON.FeatureCollection;
    },
    styleLayers: (sourceId) => [
      {
        id: `${sourceId}-points`,
        type: "circle",
        source: sourceId,
        paint: {
          // Fire radiative power (MW): small agricultural burns -> major wildfires
          "circle-color": [
            "interpolate", ["linear"], ["coalesce", ["get", "frp"], 0],
            0, "#fde047", 10, "#fb923c", 50, "#ef4444", 200, "#7f1d1d",
          ],
          "circle-radius": [
            "interpolate", ["linear"], ["zoom"],
            2, ["interpolate", ["linear"], ["coalesce", ["get", "frp"], 0], 0, 1.5, 200, 4],
            10, ["interpolate", ["linear"], ["coalesce", ["get", "frp"], 0], 0, 4, 200, 10],
          ],
          "circle-blur": 0.3,
        },
      } as LayerSpecification,
    ],
  },
  {
    id: "power-plants",
    kind: "geojson",
    category: "infrastructure",
    auth: "keyless",
    source: {
      name: "WRI Global Power Plant Database",
      url: "https://datasets.wri.org/datasets/global-power-plant-database",
      license: "CC BY 4.0",
      commercialUse: true,
      attribution: "Power plants: WRI Global Power Plant Database (CC BY 4.0)",
    },
    defaultOpacity: 0.9,
    viewportDriven: true,
    minZoom: 3,
    loadData: (viewport) => loadInfrastructure("power_plant", viewport),
    styleLayers: (sourceId) => [
      {
        id: `${sourceId}-points`,
        type: "circle",
        source: sourceId,
        paint: {
          "circle-color": FUEL_COLOR,
          // Area proportional to capacity: 1 MW -> 2 px, 10 GW -> ~14 px
          "circle-radius": ["interpolate", ["linear"], ["sqrt", ["coalesce", ["get", "capacity_mw"], 1]], 1, 2, 100, 14],
          "circle-stroke-color": "#111827",
          "circle-stroke-width": 0.5,
        },
      } as LayerSpecification,
      INFRASTRUCTURE_LABEL(sourceId, 8),
    ],
  },
  {
    id: "dams",
    kind: "geojson",
    category: "infrastructure",
    auth: "keyless",
    source: {
      name: "Global Dam Watch",
      url: "https://www.globaldamwatch.org/database",
      license: "CC BY 4.0 (© European Union / GDW)",
      commercialUse: true,
      attribution: "Dams: Global Dam Watch (CC BY 4.0)",
    },
    defaultOpacity: 0.9,
    viewportDriven: true,
    minZoom: 4,
    loadData: (viewport) => loadInfrastructure("dam", viewport),
    styleLayers: (sourceId) => [
      {
        id: `${sourceId}-points`,
        type: "circle",
        source: sourceId,
        paint: {
          "circle-color": "#22d3ee",
          "circle-radius": ["interpolate", ["linear"], ["coalesce", ["get", "height_m"], 10], 10, 2.5, 150, 8],
          "circle-stroke-color": "#0e7490",
          "circle-stroke-width": 1,
        },
      } as LayerSpecification,
      INFRASTRUCTURE_LABEL(sourceId, 8),
    ],
  },
  {
    id: "hospitals",
    kind: "style",
    category: "infrastructure",
    auth: "keyless",
    source: {
      name: "OpenStreetMap (via OpenFreeMap)",
      url: "https://www.openstreetmap.org/copyright",
      license: "ODbL",
      commercialUse: true,
      attribution: "© OpenStreetMap contributors",
    },
    defaultOpacity: 1,
    // Hospital POIs are already in the basemap's vector tiles. OpenMapTiles
    // only includes them from zoom 14 (zoom 13 tiles carry ~200 top POIs).
    basemapSource: "openmaptiles",
    styleLayers: (sourceId) => [
      {
        id: "hospitals-points",
        type: "circle",
        source: sourceId,
        "source-layer": "poi",
        minzoom: 14,
        filter: ["==", ["get", "class"], "hospital"],
        paint: {
          "circle-color": "#ef4444",
          "circle-radius": 5,
          "circle-stroke-color": "#ffffff",
          "circle-stroke-width": 1.5,
        },
      } as LayerSpecification,
      {
        id: "hospitals-labels",
        type: "symbol",
        source: sourceId,
        "source-layer": "poi",
        filter: ["==", ["get", "class"], "hospital"],
        minzoom: 15,
        layout: {
          "text-field": ["coalesce", ["get", "name"], ""],
          "text-font": LABEL_FONT,
          "text-size": 11,
          "text-offset": [0, 1],
          "text-anchor": "top",
        },
        paint: { "text-color": "#fecaca", "text-halo-color": "#111827", "text-halo-width": 1.2 },
      } as LayerSpecification,
    ],
  },
  {
    id: "satellites",
    kind: "geojson",
    category: "monitoring",
    auth: "keyless",
    source: {
      name: "CelesTrak",
      url: "https://celestrak.org/NORAD/elements/",
      // No published licence; GP data originates from the US Space Force
      license: "No explicit licence (CelesTrak usage policy)",
      commercialUse: false,
      attribution: 'Satellite orbits: <a href="https://celestrak.org">CelesTrak</a>',
    },
    defaultOpacity: 1,
    // Positions are computed server-side from cached orbits; LEO moves ~230 km in 30 s
    refreshMs: 30_000,
    loadData: async () => {
      const response = await fetch(`${API_URL}/api/v1/tracks/satellites`);
      if (!response.ok) throw new Error(`Satellites ${response.status}`);
      return (await response.json()) as GeoJSON.FeatureCollection;
    },
    styleLayers: (sourceId) => [
      {
        id: `${sourceId}-points`,
        type: "circle",
        source: sourceId,
        paint: {
          "circle-color": "#38bdf8",
          "circle-radius": ["interpolate", ["linear"], ["zoom"], 1, 2.5, 6, 5],
          "circle-stroke-color": "#0c4a6e",
          "circle-stroke-width": 1,
        },
      } as LayerSpecification,
      {
        id: `${sourceId}-labels`,
        type: "symbol",
        source: sourceId,
        minzoom: 3,
        layout: {
          "text-field": ["get", "name"],
          "text-font": LABEL_FONT,
          "text-size": 10,
          "text-offset": [0, 1],
          "text-anchor": "top",
        },
        paint: { "text-color": "#bae6fd", "text-halo-color": "#0f172a", "text-halo-width": 1.2 },
      } as LayerSpecification,
    ],
  },
  {
    id: "aircraft",
    kind: "geojson",
    category: "monitoring",
    auth: "keyless",
    source: {
      name: "adsb.lol",
      url: "https://adsb.lol",
      license: "ODbL",
      commercialUse: true,
      attribution: 'Aircraft: <a href="https://adsb.lol">adsb.lol</a> (ODbL)',
    },
    defaultOpacity: 1,
    refreshMs: 15_000,
    viewportDriven: true,
    // One upstream query covers at most 250 NM, about a zoom-5 view
    minZoom: 5,
    loadData: async ({ bbox }) => {
      const { lat, lng } = bboxCenter(bbox);
      const radiusNm = Math.min(250, Math.ceil(bboxRadiusKm(bbox) / 1.852));
      const params = new URLSearchParams({ lat: lat.toFixed(3), lng: lng.toFixed(3), radius_nm: String(radiusNm) });
      const response = await fetch(`${API_URL}/api/v1/tracks/aircraft?${params}`);
      if (!response.ok) throw new Error(`Aircraft ${response.status}`);
      return (await response.json()) as GeoJSON.FeatureCollection;
    },
    styleLayers: (sourceId) => [
      {
        id: `${sourceId}-icons`,
        type: "symbol",
        source: sourceId,
        layout: {
          // Heading arrow; aircraft without a track are drawn pointing north
          "text-field": "▲",
          "text-font": LABEL_FONT,
          "text-size": ["interpolate", ["linear"], ["zoom"], 5, 10, 10, 16],
          "text-rotate": ["coalesce", ["get", "track_deg"], 0],
          "text-rotation-alignment": "map",
          "text-allow-overlap": true,
          "text-ignore-placement": true,
        },
        paint: {
          "text-color": [
            "case",
            ["get", "military"], "#fb923c",
            ["get", "on_ground"], "#94a3b8",
            "#f1f5f9",
          ],
          "text-halo-color": "#0f172a",
          "text-halo-width": 1,
        },
      } as LayerSpecification,
      {
        id: `${sourceId}-labels`,
        type: "symbol",
        source: sourceId,
        minzoom: 8,
        layout: {
          "text-field": ["coalesce", ["get", "callsign"], ""],
          "text-font": LABEL_FONT,
          "text-size": 10,
          "text-offset": [0, 1.2],
          "text-anchor": "top",
        },
        paint: { "text-color": "#cbd5e1", "text-halo-color": "#0f172a", "text-halo-width": 1.2 },
      } as LayerSpecification,
    ],
  },
  {
    id: "vessels",
    kind: "geojson",
    category: "monitoring",
    // Needs AISSTREAM_API_KEY on the server; without it the API returns an empty list
    auth: "free_key",
    source: {
      name: "AISStream",
      url: "https://aisstream.io",
      license: "AISStream terms (no explicit licence)",
      commercialUse: false,
      attribution: 'Ships: <a href="https://aisstream.io">AISStream</a>',
    },
    defaultOpacity: 1,
    refreshMs: 15_000,
    viewportDriven: true,
    minZoom: 4,
    loadData: async ({ bbox: [west, south, east, north] }) => {
      const params = new URLSearchParams({
        min_lng: String(west),
        min_lat: String(south),
        max_lng: String(east),
        max_lat: String(north),
      });
      const response = await fetch(`${API_URL}/api/v1/tracks/vessels?${params}`);
      if (!response.ok) throw new Error(`Vessels ${response.status}`);
      return (await response.json()) as GeoJSON.FeatureCollection;
    },
    styleLayers: (sourceId) => [
      {
        id: `${sourceId}-icons`,
        type: "symbol",
        source: sourceId,
        layout: {
          "text-field": "▲",
          "text-font": LABEL_FONT,
          "text-size": ["interpolate", ["linear"], ["zoom"], 4, 9, 10, 14],
          // Heading when reported, else course over ground
          "text-rotate": ["coalesce", ["get", "heading_deg"], ["get", "course_deg"], 0],
          "text-rotation-alignment": "map",
          "text-allow-overlap": true,
          "text-ignore-placement": true,
        },
        paint: { "text-color": "#2dd4bf", "text-halo-color": "#042f2e", "text-halo-width": 1 },
      } as LayerSpecification,
      {
        id: `${sourceId}-labels`,
        type: "symbol",
        source: sourceId,
        minzoom: 8,
        layout: {
          "text-field": ["coalesce", ["get", "name"], ""],
          "text-font": LABEL_FONT,
          "text-size": 10,
          "text-offset": [0, 1.2],
          "text-anchor": "top",
        },
        paint: { "text-color": "#99f6e4", "text-halo-color": "#042f2e", "text-halo-width": 1.2 },
      } as LayerSpecification,
    ],
  },
];

/** Layers this deployment may show (commercial deployments drop NC-only sources) */
export const LAYER_DEFINITIONS: LayerDefinition[] = availableLayers(
  ALL_LAYER_DEFINITIONS,
  COMMERCIAL_DEPLOYMENT,
);

export function availableLayers(
  definitions: LayerDefinition[],
  commercial: boolean,
): LayerDefinition[] {
  return commercial ? definitions.filter((d) => d.source.commercialUse) : definitions;
}

/** Every registered layer regardless of deployment (for docs/tests) */
export { ALL_LAYER_DEFINITIONS };

export const LAYER_DEFINITIONS_BY_ID = new Map(LAYER_DEFINITIONS.map((d) => [d.id, d]));
