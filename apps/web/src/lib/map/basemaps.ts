import type {
  LayerSpecification,
  RasterSourceSpecification,
  StyleSpecification,
} from "maplibre-gl";

/**
 * Basemaps. Every map must work without API keys, and every source must have
 * licence terms we have verified from the provider:
 *
 * - dark: OpenFreeMap "dark" vector style. Free, no key, no limits, commercial
 *   use allowed; OpenMapTiles schema, OpenStreetMap data (ODbL).
 * - satellite: EOX Sentinel-2 cloudless 2025 (10 m). CC BY-NC-SA 4.0:
 *   non-commercial use (incl. NGOs) is free; commercial use needs an EOX
 *   licence. Commercial deployments fall back to NASA Blue Marble (public
 *   domain, ~500 m).
 *
 * Esri basemaps were removed: their terms could not be confirmed to allow use
 * without an ArcGIS licence. CARTO now requires an API key.
 */
export type BasemapId = "dark" | "satellite";

/** Set for commercial deployments: hides non-commercial-only sources */
export const COMMERCIAL_DEPLOYMENT = process.env.NEXT_PUBLIC_COMMERCIAL_DEPLOYMENT === "1";

export const DARK_STYLE_URL = "https://tiles.openfreemap.org/styles/dark";
/** Keyless font glyphs, used if the vector style cannot be loaded */
export const GLYPHS_URL = "https://tiles.openfreemap.org/fonts/{fontstack}/{range}.pbf";
/** A font served by OpenFreeMap; symbol layers must set text-font to this */
export const LABEL_FONT = ["Noto Sans Regular"];

export const SATELLITE_LAYER_ID = "satellite-basemap";
/** Marks layers that belong to the basemap (vs. overlays/events added later) */
const BASEMAP_TAG = "phoenix:basemap";

const EOX_SENTINEL2: RasterSourceSpecification = {
  type: "raster",
  tiles: ["https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless-2025_3857/default/g/{z}/{y}/{x}.jpg"],
  tileSize: 256,
  maxzoom: 15,
  attribution:
    '<a href="https://cloudless.eox.at">EOxCloudless</a> by EOX IT Services GmbH ' +
    "(Contains modified Copernicus Sentinel data 2025)",
};

const NASA_BLUE_MARBLE: RasterSourceSpecification = {
  type: "raster",
  tiles: [
    "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/BlueMarble_NextGeneration/default/default/GoogleMapsCompatible_Level8/{z}/{y}/{x}.jpeg",
  ],
  tileSize: 256,
  maxzoom: 8,
  attribution: "Imagery &copy; NASA Blue Marble (GIBS)",
};

export const SATELLITE_SOURCE = COMMERCIAL_DEPLOYMENT ? NASA_BLUE_MARBLE : EOX_SENTINEL2;

/** In satellite mode keep the vector style's labels on top of the imagery */
const isLabelLayer = (layer: LayerSpecification) => layer.type === "symbol";

function visibleFor(layer: LayerSpecification, active: BasemapId): boolean {
  if (layer.id === SATELLITE_LAYER_ID) return active === "satellite";
  return active === "dark" || isLabelLayer(layer);
}

function withVisibility(layer: LayerSpecification, active: BasemapId): LayerSpecification {
  const visibility = visibleFor(layer, active) ? "visible" : "none";
  return {
    ...layer,
    metadata: { ...(layer.metadata as object | undefined), [BASEMAP_TAG]: true },
    layout: { ...(layer.layout ?? {}), visibility },
  } as LayerSpecification;
}

/** Satellite-only style used when the vector style cannot be fetched */
function fallbackStyle(): StyleSpecification {
  return {
    version: 8,
    glyphs: GLYPHS_URL,
    sources: {},
    layers: [{ id: "background", type: "background", paint: { "background-color": "#111827" } }],
  };
}

/**
 * Full basemap style: the dark vector style plus the satellite raster,
 * with only `active` visible. Never throws (offline -> minimal style).
 */
export async function loadBasemapStyle(
  active: BasemapId,
  fetchImpl: typeof fetch = fetch,
): Promise<StyleSpecification> {
  let style: StyleSpecification;
  try {
    const response = await fetchImpl(DARK_STYLE_URL);
    if (!response.ok) throw new Error(`OpenFreeMap style ${response.status}`);
    style = (await response.json()) as StyleSpecification;
  } catch (error) {
    console.warn("Dark basemap unavailable; showing satellite only", error);
    style = fallbackStyle();
    active = "satellite";
  }
  const satellite: LayerSpecification = { id: SATELLITE_LAYER_ID, type: "raster", source: "satellite" };
  return {
    ...style,
    sources: { ...style.sources, satellite: SATELLITE_SOURCE },
    // Imagery at the bottom so vector labels can draw over it
    layers: [satellite, ...style.layers].map((layer) => withVisibility(layer, active)),
  };
}

/** Switch the basemap on a live map without touching overlays or events. */
export function applyBasemap(
  map: {
    getStyle(): { layers?: LayerSpecification[] } | undefined;
    setLayoutProperty(id: string, name: string, value: unknown): void;
  },
  active: BasemapId,
): void {
  for (const layer of map.getStyle()?.layers ?? []) {
    const metadata = layer.metadata as Record<string, unknown> | undefined;
    if (!metadata?.[BASEMAP_TAG]) continue;
    map.setLayoutProperty(layer.id, "visibility", visibleFor(layer, active) ? "visible" : "none");
  }
}
