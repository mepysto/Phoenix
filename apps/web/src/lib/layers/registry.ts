/**
 * Map overlay layer registry (G-1).
 *
 * Every overlay declares where its data comes from, its licence, whether it
 * needs an API key (GEV model: keyless layers always work, keys only unlock
 * more), and how to resolve its current tiles. The map, the layer panel and
 * the data-source attribution are all driven from this list.
 */

import type { LayerSpecification } from "maplibre-gl";
import { API_URL } from "@/lib/api/client";
import { COMMERCIAL_DEPLOYMENT, LABEL_FONT } from "@/lib/map/basemaps";

export type LayerCategory = "weather" | "satellite" | "hazards" | "infrastructure";

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

export interface GeoJsonLayerDefinition {
  id: string;
  kind: "geojson";
  category: LayerCategory;
  auth: LayerAuth;
  source: LayerSourceInfo;
  defaultOpacity: number;
  refreshMs?: number;
  loadData: () => Promise<GeoJSON.FeatureCollection>;
  /** MapLibre layers drawing the source, bottom to top */
  styleLayers: (sourceId: string) => LayerSpecification[];
}

export type LayerDefinition = RasterLayerDefinition | GeoJsonLayerDefinition;

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
