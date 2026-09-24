"use client";

import { useEffect, useRef, type RefObject } from "react";
import type { Map as MapLibreMap, RasterTileSource } from "maplibre-gl";
import { LAYER_DEFINITIONS, type RasterLayerDefinition } from "@/lib/layers/registry";
import { useMapStore } from "@/store/mapStore";

/** Overlays sit above the basemap but below event markers */
const EVENT_LAYER_IDS = ["clusters", "events-layer"];

const overlayId = (id: string) => `overlay-${id}`;

interface OverlayState {
  loading: boolean;
  timer: ReturnType<typeof setInterval> | null;
}

/**
 * Keep MapLibre raster overlays in sync with the layer panel.
 * Sources are added lazily on first show (no requests for hidden layers)
 * and live layers re-resolve their tiles on `refreshMs` while visible.
 */
export function useRasterOverlays(mapRef: RefObject<MapLibreMap | null>, mapReady: boolean): void {
  const layers = useMapStore((s) => s.layers);
  const states = useRef(new Map<string, OverlayState>());

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapReady) return;

    for (const definition of LAYER_DEFINITIONS) {
      const config = layers.find((l) => l.id === definition.id);
      const visible = config?.visible ?? false;
      const opacity = config?.opacity ?? definition.defaultOpacity;
      const state = states.current.get(definition.id) ?? { loading: false, timer: null };
      states.current.set(definition.id, state);
      const id = overlayId(definition.id);

      if (visible && !map.getSource(id) && !state.loading) {
        state.loading = true;
        void addOverlay(map, definition, opacity).finally(() => {
          state.loading = false;
        });
      }

      if (map.getLayer(id)) {
        map.setLayoutProperty(id, "visibility", visible ? "visible" : "none");
        map.setPaintProperty(id, "raster-opacity", opacity);
      }

      if (visible && definition.refreshMs && !state.timer) {
        state.timer = setInterval(() => void refreshOverlay(map, definition), definition.refreshMs);
      } else if (!visible && state.timer) {
        clearInterval(state.timer);
        state.timer = null;
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

async function addOverlay(map: MapLibreMap, definition: RasterLayerDefinition, opacity: number) {
  const id = overlayId(definition.id);
  try {
    const { tiles, maxzoom, tileSize = 256 } = await definition.resolveTiles(new Date());
    if (map.getSource(id)) return; // added by a concurrent call
    map.addSource(id, {
      type: "raster",
      tiles,
      tileSize,
      maxzoom,
      attribution: definition.source.attribution,
    });
    const beforeId = EVENT_LAYER_IDS.find((layerId) => map.getLayer(layerId));
    map.addLayer(
      { id, type: "raster", source: id, paint: { "raster-opacity": opacity } },
      beforeId,
    );
  } catch (error) {
    console.warn(`Overlay "${definition.id}" is unavailable`, error);
  }
}

async function refreshOverlay(map: MapLibreMap, definition: RasterLayerDefinition) {
  try {
    const { tiles } = await definition.resolveTiles(new Date());
    (map.getSource(overlayId(definition.id)) as RasterTileSource | undefined)?.setTiles(tiles);
  } catch (error) {
    // Keep showing the last frame rather than blanking the layer
    console.warn(`Overlay "${definition.id}" refresh failed`, error);
  }
}
