/**
 * Map overlay layer registry (G-1).
 *
 * Every overlay declares where its data comes from, its licence, whether it
 * needs an API key (GEV model: keyless layers always work, keys only unlock
 * more), and how to resolve its current tiles. The map, the layer panel and
 * the data-source attribution are all driven from this list.
 */

import { COMMERCIAL_DEPLOYMENT } from "@/lib/map/basemaps";

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

export type LayerDefinition = RasterLayerDefinition;

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
