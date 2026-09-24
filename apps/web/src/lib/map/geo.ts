import { wrapLng } from "@/lib/map/viewport";

const EARTH_RADIUS_KM = 6371;
const toRad = (deg: number) => (deg * Math.PI) / 180;

/** Great-circle distance in km */
export function haversineKm(a: { lat: number; lng: number }, b: { lat: number; lng: number }): number {
  const dLat = toRad(b.lat - a.lat);
  const dLng = toRad(b.lng - a.lng);
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(toRad(a.lat)) * Math.cos(toRad(b.lat)) * Math.sin(dLng / 2) ** 2;
  return 2 * EARTH_RADIUS_KM * Math.asin(Math.min(1, Math.sqrt(h)));
}

/** Centre of [west, south, east, north], including a box crossing the antimeridian (west > east) */
export function bboxCenter([west, south, east, north]: [number, number, number, number]): { lat: number; lng: number } {
  const span = east >= west ? east - west : east + 360 - west;
  return { lat: (south + north) / 2, lng: wrapLng(west + span / 2) };
}

/** Radius (km) of the circle around the bbox centre that reaches its corners */
export function bboxRadiusKm(bbox: [number, number, number, number]): number {
  const center = bboxCenter(bbox);
  const [west, south, , north] = bbox;
  return Math.max(haversineKm(center, { lat: north, lng: west }), haversineKm(center, { lat: south, lng: west }));
}
