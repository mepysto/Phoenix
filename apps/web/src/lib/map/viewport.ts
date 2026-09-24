import type { Map as MapLibreMap } from "maplibre-gl";
import type { Viewport } from "@/lib/layers/registry";

/** Longitude normalised to [-180, 180) */
export const wrapLng = (lng: number) => ((((lng + 180) % 360) + 360) % 360) - 180;

/** A layer viewport plus the true screen centre (not the bbox midpoint on a projected map) */
export interface MapViewport extends Viewport {
  center: { lat: number; lng: number };
}

/** The map's visible bbox; the whole world once zoomed out past one world width */
export function currentViewport(map: MapLibreMap): MapViewport {
  const bounds = map.getBounds();
  let west = bounds.getWest();
  let east = bounds.getEast();
  // Zoomed out past a full world width (or a wrapped globe): query everything
  if (east - west >= 360) {
    west = -180;
    east = 180;
  }
  return {
    bbox: [
      west === -180 ? -180 : wrapLng(west),
      Math.max(bounds.getSouth(), -90),
      east === 180 ? 180 : wrapLng(east),
      Math.min(bounds.getNorth(), 90),
    ],
    zoom: map.getZoom(),
    center: { lat: map.getCenter().lat, lng: wrapLng(map.getCenter().lng) },
  };
}
