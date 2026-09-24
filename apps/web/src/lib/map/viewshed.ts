/**
 * Approximate camera coverage (G-10). Public camera feeds usually report only
 * a compass direction, not a field of view or range, so coverage is drawn as
 * a fixed wedge: a rough guide to what a camera can see, not a measurement.
 */

const BEARING: Record<string, number> = { north: 0, east: 90, south: 180, west: 270 };
export const VIEW_ANGLE_DEG = 60;
export const VIEW_RANGE_M = 300;

export function directionBearing(direction: unknown): number | null {
  if (typeof direction !== "string") return null;
  return BEARING[direction.trim().toLowerCase()] ?? null;
}

/** Wedge polygon from a point toward a bearing (degrees clockwise from north) */
export function wedge(
  lng: number,
  lat: number,
  bearing: number,
  angleDeg = VIEW_ANGLE_DEG,
  rangeM = VIEW_RANGE_M,
  steps = 8,
): GeoJSON.Polygon {
  const dLat = rangeM / 111_320;
  const dLng = rangeM / (111_320 * Math.cos((lat * Math.PI) / 180));
  const ring: [number, number][] = [[lng, lat]];
  for (let i = 0; i <= steps; i++) {
    const angle = ((bearing - angleDeg / 2 + (angleDeg * i) / steps) * Math.PI) / 180;
    ring.push([lng + dLng * Math.sin(angle), lat + dLat * Math.cos(angle)]);
  }
  ring.push([lng, lat]);
  return { type: "Polygon", coordinates: [ring] };
}

/** Add a coverage wedge for every camera point with a known direction */
export function withViewsheds(collection: GeoJSON.FeatureCollection): GeoJSON.FeatureCollection {
  const wedges: GeoJSON.Feature[] = [];
  for (const feature of collection.features) {
    if (feature.geometry.type !== "Point") continue;
    const bearing = directionBearing(feature.properties?.direction);
    if (bearing === null) continue;
    const [lng, lat] = feature.geometry.coordinates as [number, number];
    wedges.push({ type: "Feature", geometry: wedge(lng, lat, bearing), properties: { kind: "viewshed" } });
  }
  return { ...collection, features: [...wedges, ...collection.features] };
}
