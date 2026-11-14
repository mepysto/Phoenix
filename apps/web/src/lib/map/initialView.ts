/**
 * The first view of the globe when the URL does not set one (UX plan 5.1):
 * large enough to fill most of the map area, turned toward the reader.
 */

/** Globe diameter in CSS pixels at zoom 0 (MapLibre globe, 512px tiles; measured) */
const GLOBE_PX_AT_ZOOM_0 = 140;
const FILL = 0.85;
const DEFAULT_LAT = 20;

/** Longitude the reader's clock points at: UTC+9 faces 135°E. No location prompt. */
export function longitudeFromTimezone(offsetMinutes: number): number {
  const lng = (-offsetMinutes / 60) * 15;
  return Math.max(-180, Math.min(180, lng)) + 0; // + 0 turns -0 into 0
}

export function initialView(
  width: number,
  height: number,
  timezoneOffsetMinutes = new Date().getTimezoneOffset(),
): { lng: number; lat: number; zoom: number } {
  const size = Math.max(1, Math.min(width, height));
  const zoom = Math.log2((FILL * size) / GLOBE_PX_AT_ZOOM_0);
  return {
    lng: longitudeFromTimezone(timezoneOffsetMinutes),
    lat: DEFAULT_LAT,
    zoom: Math.round(Math.max(0.5, Math.min(3, zoom)) * 100) / 100,
  };
}
