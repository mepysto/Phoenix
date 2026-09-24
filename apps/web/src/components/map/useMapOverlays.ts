"use client";

import { useEffect, useRef, type RefObject } from "react";
import type {
  GeoJSONSource,
  LayerSpecification,
  Map as MapLibreMap,
  RasterTileSource,
} from "maplibre-gl";
import { LAYER_DEFINITIONS, type LayerDefinition } from "@/lib/layers/registry";
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

      if (visible && !map.getSource(sourceIdFor(definition.id)) && !current.loading) {
        current.loading = true;
        void addOverlay(map, definition, current)
          .then(() => applyDisplay(map, current, true, opacity))
          .finally(() => {
            current.loading = false;
          });
      }

      applyDisplay(map, current, visible, opacity);

      if (visible && definition.refreshMs && !current.timer) {
        current.timer = setInterval(() => void refreshOverlay(map, definition), definition.refreshMs);
      } else if (!visible && current.timer) {
        clearInterval(current.timer);
        current.timer = null;
      }
    }
  }, [layers, mapReady, mapRef]);

  useEffect(() => {
    const current = states.current;
    return () => {
      for (const state of current.values()) if (state.timer) clearInterval(state.timer);
    };
  }, []);
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
    } else {
      const data = await definition.loadData();
      if (map.getSource(sourceId)) return;
      map.addSource(sourceId, { type: "geojson", data, attribution: definition.source.attribution });
      styleLayers = definition.styleLayers(sourceId);
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
    } else {
      (source as GeoJSONSource | undefined)?.setData(await definition.loadData());
    }
  } catch (error) {
    // Keep the last good data rather than blanking the layer
    console.warn(`Overlay "${definition.id}" refresh failed`, error);
  }
}
