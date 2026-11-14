/**
 * Before/after satellite comparison around an event.
 *
 * Uses NASA GIBS daily VIIRS true-colour mosaics (keyless, no restrictions on
 * use). A 3x3 block of web-mercator tiles is centred on the event so the
 * event sits near the middle of the view.
 */

const GIBS = "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best";
export const COMPARE_LAYER = "VIIRS_SNPP_CorrectedReflectance_TrueColor";
// The layer's tile matrix set tops out at level 9
export const COMPARE_MAX_ZOOM = 9;
const DAY_MS = 86_400_000;

export interface TileRef {
  x: number;
  y: number;
  /** Position of the tile in the 3x3 grid, 0..2 */
  col: number;
  row: number;
}

export interface TileGrid {
  z: number;
  tiles: TileRef[];
  /** Where the event falls inside the 768px grid, in pixels */
  focus: { x: number; y: number };
}

/** Fractional web-mercator tile coordinates of a point */
export function tileCoords(
  lat: number,
  lng: number,
  z: number,
): { x: number; y: number } {
  const n = 2 ** z;
  const clamped = Math.max(-85.0511, Math.min(85.0511, lat));
  const rad = (clamped * Math.PI) / 180;
  const x = ((lng + 180) / 360) * n;
  const y =
    ((1 - Math.log(Math.tan(rad) + 1 / Math.cos(rad)) / Math.PI) / 2) * n;
  return { x, y };
}

/** 3x3 tiles around the point; x wraps across the antimeridian, y is clamped */
export function tileGrid(lat: number, lng: number, z: number): TileGrid {
  const n = 2 ** z;
  const { x, y } = tileCoords(lat, lng, z);
  const cx = Math.floor(x);
  const cy = Math.min(n - 2, Math.max(1, Math.floor(y)));
  const tiles: TileRef[] = [];
  for (let row = 0; row < 3; row++) {
    for (let col = 0; col < 3; col++) {
      tiles.push({
        x: (((cx - 1 + col) % n) + n) % n,
        y: cy - 1 + row,
        col,
        row,
      });
    }
  }
  return {
    z,
    tiles,
    focus: { x: (x - (cx - 1)) * 256, y: (y - (cy - 1)) * 256 },
  };
}

export function isoDate(d: Date): string {
  return d.toISOString().slice(0, 10);
}

export function compareTileUrl(
  date: string,
  z: number,
  t: Pick<TileRef, "x" | "y">,
): string {
  return `${GIBS}/${COMPARE_LAYER}/default/${date}/GoogleMapsCompatible_Level9/${z}/${t.y}/${t.x}.jpg`;
}

/** Daily mosaics are assembled over about two days; later ones may still have gaps */
const MOSAIC_LAG_MS = 2 * DAY_MS;
const BEFORE_MS = 7 * DAY_MS;

/**
 * Default dates (UX plan 5.3): a week before onset, so the "before" view is
 * clearly pre-event and likely cloud-free on some day nearby, and two days
 * after onset, never later than the newest complete mosaic.
 */
export function defaultCompareDates(
  start: Date,
  now: Date = new Date(),
): { before: string; after: string } {
  const before = new Date(start.getTime() - BEFORE_MS);
  const latestComplete = new Date(now.getTime() - MOSAIC_LAG_MS);
  const afterTarget = new Date(start.getTime() + MOSAIC_LAG_MS);
  const after = afterTarget < latestComplete ? afterTarget : latestComplete;
  return {
    before: isoDate(before),
    after: isoDate(after < before ? before : after),
  };
}

/** Whether imagery from after the onset can exist yet */
export function compareReady(start: Date, now: Date = new Date()): boolean {
  return now.getTime() - start.getTime() >= MOSAIC_LAG_MS;
}

/** Zoom that suits the event: tighter for local events, wider for storms */
export function compareZoom(type: string): number {
  switch (type) {
    case "hurricane":
    case "storm":
    case "drought":
    case "coldwave":
    case "heatwave":
      return 5;
    case "flood":
    case "wildfire":
      return 7;
    default:
      return 8;
  }
}
