import type { Map as MapLibreMap } from "maplibre-gl";

/**
 * The live MapLibre map, for tools that draw their own layers or take map
 * clicks (route planner). Set by GlobeViewer while its map is ready.
 */
let current: MapLibreMap | null = null;

export function setMapInstance(map: MapLibreMap | null): void {
  current = map;
}

export function getMapInstance(): MapLibreMap | null {
  return current;
}
