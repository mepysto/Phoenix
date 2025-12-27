import { create, StateCreator } from "zustand";
import { devtools, DevtoolsOptions } from "zustand/middleware";
import type { ViewerConfig, LayerConfig } from "@phoenix/shared/types";

interface MapState {
  viewerConfig: ViewerConfig;
  layers: LayerConfig[];
  is3D: boolean;
  center: { lng: number; lat: number };
  zoom: number;
  engine: "maplibre" | "cesium";
  basemap: "dark" | "satellite";
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
}

type MapStore = MapState & MapActions;

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
  {
    id: "buildings",
    name: "3D Buildings",
    type: "3d-tiles",
    visible: false,
    opacity: 1,
    order: 50,
  },
  {
    id: "population",
    name: "Population Density",
    type: "raster",
    visible: false,
    opacity: 0.7,
    order: 10,
  },
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
