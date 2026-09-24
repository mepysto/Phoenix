/** Layer registry types (G-1) */

import type { LayerSpecification } from "maplibre-gl";

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
  /** Clicking a feature opens its details card (see FeatureInspector) */
  inspectable?: boolean;
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
