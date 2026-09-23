import type { ApiDisasterEvent } from "@/lib/api/client";

export interface LatLng {
  lat: number;
  lng: number;
}

/**
 * Where to draw an event on a map.
 *
 * Prefers the API's display point (exact coordinates, or an admin/country
 * centroid for events that only have a region), then raw coordinates.
 * Returns null when the event cannot be placed at all.
 */
export function getEventPosition(event: Pick<ApiDisasterEvent, "location" | "displayPoint">): LatLng | null {
  const point = event.displayPoint;
  if (point) return { lat: point.lat, lng: point.lng };
  const { lat, lng } = event.location;
  if (lat == null || lng == null) return null;
  return { lat, lng };
}

/** Human-readable coordinates, or a dash when the event has no position. */
export function formatPosition(position: LatLng | null, digits = 2): string {
  if (!position) return "—";
  return `${position.lat.toFixed(digits)}, ${position.lng.toFixed(digits)}`;
}
