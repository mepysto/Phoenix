"use client";

import { useEffect, useRef, type RefObject } from "react";
import type {
  GeoJSONSource,
  LayerSpecification,
  Map as MapLibreMap,
  MapMouseEvent,
  PointLike,
  RasterTileSource,
} from "maplibre-gl";
import {
  LAYER_DEFINITIONS,
  type GeoJsonLayerDefinition,
  type LayerDefinition,
} from "@/lib/layers/registry";
import { currentViewport } from "@/lib/map/viewport";
import { useMapStore } from "@/store/mapStore";

/** Overlays sit above the basemap but below event markers */
const EVENT_LAYER_IDS = ["clusters", "events-layer"];

const sourceIdFor = (id: string) => `overlay-${id}`;

/** Paint property controlling opacity for each MapLibre layer type */
const OPACITY_PROPERTY: Partial<Record<LayerSpecification["type"], string>> = {
  raster: "raster-opacity",
  fill: "fill-opacity",
  line: "line-opacity",
  circle: "circle-opacity",
  symbol: "text-opacity",
};

interface OverlayState {
  loading: boolean;
  timer: ReturnType<typeof setInterval> | null;
  /** Map layer ids created for this overlay */
  layerIds: string[];
  /** Style-defined opacity per layer, scaled by the user's opacity slider */
  baseOpacity: Map<string, number>;
}

/**
 * Keep MapLibre overlays (raster tiles and GeoJSON hazard layers) in sync
 * with the layer panel. Sources are added lazily on first show (hidden layers
 * make no requests) and live layers refresh on `refreshMs` while visible.
 */
export function useMapOverlays(mapRef: RefObject<MapLibreMap | null>, mapReady: boolean): void {
  const layers = useMapStore((s) => s.layers);
  const states = useRef(new Map<string, OverlayState>());

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapReady) return;

    for (const definition of LAYER_DEFINITIONS) {
      const config = layers.find((l) => l.id === definition.id);
      const visible = config?.visible ?? false;
      const opacity = config?.opacity ?? definition.defaultOpacity;
      let state = states.current.get(definition.id);
      if (!state) {
        state = { loading: false, timer: null, layerIds: [], baseOpacity: new Map() };
        states.current.set(definition.id, state);
      }
      const current = state;

      if (visible) ensureAdded(map, definition, current, opacity);

      applyDisplay(map, current, visible, opacity);

      const refreshMs = "refreshMs" in definition ? definition.refreshMs : undefined;
      if (visible && refreshMs && !current.timer) {
        current.timer = setInterval(() => {
          // Retry a failed first load, otherwise refresh the data
          if (ensureAdded(map, definition, current, opacity)) void refreshOverlay(map, definition);
        }, refreshMs);
      } else if (!visible && current.timer) {
        clearInterval(current.timer);
        current.timer = null;
      }
    }
  }, [layers, mapReady, mapRef]);

  // Viewport-driven layers re-query after the map settles
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapReady) return;
    let timer: ReturnType<typeof setTimeout> | null = null;
    const onMoveEnd = () => {
      if (timer) clearTimeout(timer);
      timer = setTimeout(() => {
        const visible = new Map(
          useMapStore.getState().layers.filter((l) => l.visible).map((l) => [l.id, l.opacity]),
        );
        for (const definition of LAYER_DEFINITIONS) {
          const opacity = visible.get(definition.id);
          const state = states.current.get(definition.id);
          if (opacity === undefined || !state) continue;
          // Moving the map also retries overlays whose first load failed
          const added = ensureAdded(map, definition, state, opacity);
          if (added && definition.kind === "geojson" && definition.viewportDriven) {
            void refreshOverlay(map, definition);
          }
        }
      }, VIEWPORT_DEBOUNCE_MS);
    };
    map.on("moveend", onMoveEnd);
    return () => {
      map.off("moveend", onMoveEnd);
      if (timer) clearTimeout(timer);
    };
  }, [mapReady, mapRef]);

  // Inspectable overlays: a click opens the feature's card, hovering shows a pointer
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapReady) return;
    const inspectableLayerIds = () =>
      LAYER_DEFINITIONS.filter((d) => d.kind === "geojson" && d.inspectable)
        .flatMap((d) => states.current.get(d.id)?.layerIds ?? [])
        .filter((id) => map.getLayer(id) && map.getLayoutProperty(id, "visibility") !== "none");
    const featureAt = (point: PointLike) => {
      const layers = inspectableLayerIds();
      return layers.length ? map.queryRenderedFeatures(point, { layers })[0] : undefined;
    };
    const onClick = (e: MapMouseEvent) => {
      const feature = featureAt(e.point);
      if (!feature || feature.geometry.type !== "Point") return;
      const [lng, lat] = feature.geometry.coordinates as [number, number];
      useMapStore.getState().setInspected({
        layerId: String(feature.source).replace(/^overlay-/, ""),
        properties: feature.properties ?? {},
        lng,
        lat,
      });
    };
    // Only undo a pointer we set (event markers manage their own cursor)
    let pointing = false;
    const onMove = (e: MapMouseEvent) => {
      const over = !!featureAt(e.point);
      if (over !== pointing) {
        map.getCanvas().style.cursor = over ? "pointer" : "";
        pointing = over;
      }
    };
    map.on("click", onClick);
    map.on("mousemove", onMove);
    return () => {
      map.off("click", onClick);
      map.off("mousemove", onMove);
    };
  }, [mapReady, mapRef]);

  useEffect(() => {
    const current = states.current;
    return () => {
      for (const state of current.values()) if (state.timer) clearInterval(state.timer);
    };
  }, []);
}

const VIEWPORT_DEBOUNCE_MS = 400;
const EMPTY: GeoJSON.FeatureCollection = { type: "FeatureCollection", features: [] };

/** Viewport data for a GeoJSON layer; empty below its minimum zoom */
async function loadGeoJson(map: MapLibreMap, definition: GeoJsonLayerDefinition) {
  const viewport = currentViewport(map);
  if (definition.minZoom !== undefined && viewport.zoom < definition.minZoom) return EMPTY;
  return definition.loadData(viewport);
}

function applyDisplay(map: MapLibreMap, state: OverlayState, visible: boolean, opacity: number) {
  for (const layerId of state.layerIds) {
    const layer = map.getLayer(layerId);
    if (!layer) continue;
    map.setLayoutProperty(layerId, "visibility", visible ? "visible" : "none");
    const property = OPACITY_PROPERTY[layer.type as LayerSpecification["type"]];
    if (property) {
      map.setPaintProperty(layerId, property, (state.baseOpacity.get(layerId) ?? 1) * opacity);
    }
  }
}

/** Add the overlay if it is visible but missing (e.g. its first load failed) */
function ensureAdded(map: MapLibreMap, definition: LayerDefinition, state: OverlayState, opacity: number): boolean {
  const added =
    definition.kind === "style" ? state.layerIds.length > 0 : !!map.getSource(sourceIdFor(definition.id));
  if (added || state.loading) return added;
  state.loading = true;
  void addOverlay(map, definition, state)
    .then(() => applyDisplay(map, state, true, opacity))
    .finally(() => {
      state.loading = false;
    });
  return false;
}

async function addOverlay(map: MapLibreMap, definition: LayerDefinition, state: OverlayState) {
  const sourceId = sourceIdFor(definition.id);
  const beforeId = EVENT_LAYER_IDS.find((layerId) => map.getLayer(layerId));
  try {
    let styleLayers: LayerSpecification[];
    if (definition.kind === "raster") {
      const { tiles, maxzoom, tileSize = 256 } = await definition.resolveTiles(new Date());
      if (map.getSource(sourceId)) return; // added by a concurrent call
      map.addSource(sourceId, {
        type: "raster",
        tiles,
        tileSize,
        maxzoom,
        attribution: definition.source.attribution,
      });
      styleLayers = [{ id: sourceId, type: "raster", source: sourceId }];
    } else if (definition.kind === "geojson") {
      const data = await loadGeoJson(map, definition);
      if (map.getSource(sourceId)) return;
      map.addSource(sourceId, { type: "geojson", data, attribution: definition.source.attribution });
      styleLayers = definition.styleLayers(sourceId);
    } else {
      // Draw from the basemap's own source; nothing to download
      if (!map.getSource(definition.basemapSource)) return;
      styleLayers = definition.styleLayers(definition.basemapSource);
    }
    for (const layer of styleLayers) {
      const property = OPACITY_PROPERTY[layer.type];
      const paint = (layer as { paint?: Record<string, unknown> }).paint ?? {};
      const base = property && typeof paint[property] === "number" ? (paint[property] as number) : 1;
      state.baseOpacity.set(layer.id, base);
      map.addLayer(layer, beforeId);
      state.layerIds.push(layer.id);
    }
  } catch (error) {
    console.warn(`Overlay "${definition.id}" is unavailable`, error);
  }
}

async function refreshOverlay(map: MapLibreMap, definition: LayerDefinition) {
  const source = map.getSource(sourceIdFor(definition.id));
  try {
    if (definition.kind === "raster") {
      const { tiles } = await definition.resolveTiles(new Date());
      (source as RasterTileSource | undefined)?.setTiles(tiles);
    } else if (definition.kind === "geojson") {
      (source as GeoJSONSource | undefined)?.setData(await loadGeoJson(map, definition));
    }
  } catch (error) {
    // Keep the last good data rather than blanking the layer
    console.warn(`Overlay "${definition.id}" refresh failed`, error);
  }
}
