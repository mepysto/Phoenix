/** API limits for GET /geodata/nearby */
const MIN_RADIUS_KM = 25;
const MAX_RADIUS_KM = 5000;

/** Search radius that roughly matches what is visible at a zoom level */
export function nearbyRadiusKm(zoom: number): number {
  const km = 40_000 / 2 ** zoom; // Earth's circumference over the world widths shown
  return Math.round(Math.min(MAX_RADIUS_KM, Math.max(MIN_RADIUS_KM, km)));
}
