import { create, StateCreator } from "zustand";
import { devtools, DevtoolsOptions } from "zustand/middleware";
import type { ViewerConfig, LayerConfig } from "@phoenix/shared/types";
import { LAYER_DEFINITIONS } from "@/lib/layers/registry";
import type { MapView } from "@/lib/map/urlState";
import type { MapViewport } from "@/lib/map/viewport";

interface MapState {
  viewerConfig: ViewerConfig;
  layers: LayerConfig[];
  is3D: boolean;
  center: { lng: number; lat: number };
  zoom: number;
  engine: "maplibre" | "cesium";
  basemap: "dark" | "satellite";
  /** Visible area after the last move; null until the map has loaded */
  viewport: MapViewport | null;
  /** Camera move asked for by something other than the map (e.g. a brief); seq makes repeats distinct */
  cameraRequest: { view: MapView; seq: number } | null;
  /** Feature of an inspectable overlay the user clicked (camera, aircraft, ...) */
  inspected: InspectedFeature | null;
}

export interface InspectedFeature {
  layerId: string;
  properties: Record<string, unknown>;
  lng: number;
  lat: number;
}

interface MapActions {
  setViewerMode: (mode: "2d" | "3d") => void;
  setBaseLayer: (layer: "osm" | "satellite" | "terrain") => void;
  toggleTerrain: (enabled: boolean) => void;
  toggleBuildings: (enabled: boolean) => void;
  toggleLayer: (layerId: string) => void;
  setLayerOpacity: (layerId: string, opacity: number) => void;
  setCenter: (lng: number, lat: number) => void;
  setZoom: (zoom: number) => void;
  flyTo: (lng: number, lat: number, zoom?: number) => void;
  setEngine: (engine: "maplibre" | "cesium") => void;
  toggleEngine: () => void;
  setBasemap: (basemap: "dark" | "satellite") => void;
  toggleBasemap: () => void;
  setViewport: (viewport: MapViewport) => void;
  requestCamera: (view: MapView) => void;
  /** Show exactly these overlay layers (registry layers only; base layers are untouched) */
  showOnlyOverlays: (ids: string[]) => void;
  setOverlaysVisible: (show: string[], hide: string[]) => void;
  setInspected: (feature: InspectedFeature | null) => void;
}

type MapStore = MapState & MapActions;

const OVERLAY_IDS = new Set(LAYER_DEFINITIONS.map((definition) => definition.id));

const defaultLayers: LayerConfig[] = [
  {
    id: "events",
    name: "Disaster Events",
    type: "markers",
    visible: true,
    opacity: 1,
    order: 100,
  },
  {
    id: "satellite",
    name: "Satellite Imagery",
    type: "raster",
    visible: true,
    opacity: 1,
    order: 1,
  },
  // Overlays from the layer registry, hidden until the user turns them on
  ...LAYER_DEFINITIONS.map(
    (definition, index): LayerConfig => ({
      id: definition.id,
      name: definition.source.name,
      type: definition.kind,
      visible: false,
      opacity: definition.defaultOpacity,
      order: 10 + index,
    }),
  ),
];

const initialState: MapState = {
  viewerConfig: {
    mode: "3d",
    baseLayer: "satellite",
    terrain: { enabled: true, provider: "cesium-world-terrain" },
    buildings: { enabled: false },
  },
  layers: defaultLayers,
  is3D: true,
  center: { lng: 0, lat: 20 },
  viewport: null,
  cameraRequest: null,
  inspected: null,
  zoom: 2,
  engine: "maplibre",
  basemap: "dark",
};

const storeImpl: StateCreator<MapStore, [], []> = (set) => ({
  ...initialState,

  setViewerMode: (mode) => {
    set((state) => ({
      viewerConfig: { ...state.viewerConfig, mode },
      is3D: mode === "3d",
    }));
  },

  setBaseLayer: (layer) => {
    set((state) => ({
      viewerConfig: { ...state.viewerConfig, baseLayer: layer },
    }));
  },

  toggleTerrain: (enabled) => {
    set((state) => ({
      viewerConfig: {
        ...state.viewerConfig,
        terrain: { ...state.viewerConfig.terrain, enabled },
      },
    }));
  },

  toggleBuildings: (enabled) => {
    set((state) => ({
      viewerConfig: {
        ...state.viewerConfig,
        buildings: { ...state.viewerConfig.buildings, enabled },
      },
    }));
  },

  toggleLayer: (layerId) => {
    set((state) => ({
      layers: state.layers.map((layer) =>
        layer.id === layerId ? { ...layer, visible: !layer.visible } : layer,
      ),
    }));
  },

  setLayerOpacity: (layerId, opacity) => {
    set((state) => ({
      layers: state.layers.map((layer) =>
        layer.id === layerId ? { ...layer, opacity } : layer,
      ),
    }));
  },

  setCenter: (lng, lat) => {
    set({ center: { lng, lat } });
  },

  setViewport: (viewport) => {
    set({ viewport });
  },

  requestCamera: (view) => {
    set((state) => ({ cameraRequest: { view, seq: (state.cameraRequest?.seq ?? 0) + 1 } }));
  },

  setInspected: (inspected) => {
    set({ inspected });
  },

  setOverlaysVisible: (show, hide) => {
    const on = new Set(show);
    const off = new Set(hide);
    set((state) => ({
      layers: state.layers.map((layer) =>
        !OVERLAY_IDS.has(layer.id)
          ? layer
          : on.has(layer.id)
            ? { ...layer, visible: true }
            : off.has(layer.id)
              ? { ...layer, visible: false }
              : layer,
      ),
    }));
  },

  showOnlyOverlays: (ids) => {
    const wanted = new Set(ids);
    set((state) => ({
      layers: state.layers.map((layer) =>
        OVERLAY_IDS.has(layer.id) ? { ...layer, visible: wanted.has(layer.id) } : layer,
      ),
    }));
  },

  setZoom: (zoom) => {
    set({ zoom });
  },

  flyTo: (lng, lat, zoom) => {
    set((state) => ({
      center: { lng, lat },
      zoom: zoom ?? state.zoom,
    }));
  },

  setEngine: (engine) => {
    set({ engine });
  },

  toggleEngine: () => {
    set((state) => ({
      engine: state.engine === "maplibre" ? "cesium" : "maplibre",
    }));
  },

  setBasemap: (basemap) => {
    set({ basemap });
  },

  toggleBasemap: () => {
    set((state) => ({
      basemap: state.basemap === "dark" ? "satellite" : "dark",
    }));
  },
});

const withDevtools = <T>(
  impl: StateCreator<T, [], []>,
  options: DevtoolsOptions,
): StateCreator<T, [], []> => {
  if (process.env.NODE_ENV === "development") {
    return devtools(impl, options) as unknown as StateCreator<T, [], []>;
  }
  return impl;
};

export const useMapStore = create<MapStore>()(
  withDevtools(storeImpl, { name: "map-store" }),
);
