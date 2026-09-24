import type {
  LayerSpecification,
  SourceSpecification,
  StyleSpecification,
} from "maplibre-gl";

/**
 * Keyless basemaps. Every map must work without API keys (keys may only
 * upgrade a layer, never gate it). CARTO basemaps started requiring a key
 * and rendered "API KEY REQUIRED" watermarks, so they are not used.
 */
export type BasemapId = "dark" | "satellite";

const ESRI_ATTRIBUTION =
  "Tiles &copy; Esri &mdash; Esri, HERE, Garmin, &copy; OpenStreetMap contributors";

const SOURCES: Record<string, SourceSpecification> = {
  darkBase: {
    type: "raster",
    tiles: [
      "https://services.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}",
    ],
    tileSize: 256,
    maxzoom: 16,
    attribution: ESRI_ATTRIBUTION,
  },
  darkLabels: {
    type: "raster",
    tiles: [
      "https://services.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Reference/MapServer/tile/{z}/{y}/{x}",
    ],
    tileSize: 256,
    maxzoom: 16,
  },
  satellite: {
    type: "raster",
    tiles: [
      "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    ],
    tileSize: 256,
    maxzoom: 19,
    attribution: "Tiles &copy; Esri &mdash; Esri, Maxar, Earthstar Geographics",
  },
};

/** Map layers that make up each basemap, bottom to top. */
export const BASEMAP_LAYERS: Record<BasemapId, { id: string; source: string }[]> = {
  dark: [
    { id: "dark-basemap", source: "darkBase" },
    { id: "dark-labels", source: "darkLabels" },
  ],
  satellite: [{ id: "satellite-basemap", source: "satellite" }],
};

/** Keyless font glyphs (MapLibre's demotiles server is for demos only). */
export const GLYPHS_URL = "https://tiles.openfreemap.org/fonts/{fontstack}/{range}.pbf";
/** A font served at GLYPHS_URL; symbol layers must set text-font to this. */
export const LABEL_FONT = ["Noto Sans Regular"];

/** Base style with every basemap loaded and only `active` visible. */
export function createBasemapStyle(active: BasemapId): StyleSpecification {
  const layers: LayerSpecification[] = (Object.keys(BASEMAP_LAYERS) as BasemapId[]).flatMap(
    (basemap) =>
      BASEMAP_LAYERS[basemap].map(
        ({ id, source }): LayerSpecification => ({
          id,
          type: "raster",
          source,
          layout: { visibility: basemap === active ? "visible" : "none" },
        }),
      ),
  );
  return { version: 8, sources: SOURCES, layers, glyphs: GLYPHS_URL };
}

/** Show `active` and hide every other basemap on a live map. */
export function applyBasemap(
  map: { getLayer(id: string): unknown; setLayoutProperty(id: string, name: string, value: unknown): void },
  active: BasemapId,
): void {
  for (const basemap of Object.keys(BASEMAP_LAYERS) as BasemapId[]) {
    for (const { id } of BASEMAP_LAYERS[basemap]) {
      if (map.getLayer(id)) {
        map.setLayoutProperty(id, "visibility", basemap === active ? "visible" : "none");
      }
    }
  }
}
