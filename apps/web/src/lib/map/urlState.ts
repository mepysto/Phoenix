import { EVENT_TYPES } from "@phoenix/shared/constants";
import type { EventType, SeverityLevel } from "@/lib/api/client";
import type { BasemapId } from "./basemaps";

/**
 * Shareable map state in the query string (G-4 deep links).
 *
 *   ?v=lng,lat,zoom,bearing,pitch&p=2d&b=satellite&t=flood,storm&s=high&event=<id>&time=2026-09-01T06:00Z
 *   (t = event types, time = timeline instant)
 *
 * Only non-default values are written, and anything invalid in an incoming
 * URL is dropped rather than breaking the page.
 */
export interface MapView {
  lng: number;
  lat: number;
  zoom: number;
  bearing: number;
  pitch: number;
}

export interface MapUrlState {
  view?: MapView;
  projection?: "globe" | "mercator";
  basemap?: BasemapId;
  /** Visible event types; undefined = all */
  types?: EventType[];
  /** Visible severities; undefined = all */
  severities?: SeverityLevel[];
  /** Event to focus (open its card) */
  event?: string;
  /** Timeline instant (ISO); absent = live */
  at?: string;
}

export const ALL_SEVERITY_LEVELS: SeverityLevel[] = ["low", "medium", "high", "critical"];
const BASEMAPS: BasemapId[] = ["dark", "satellite"];
const EVENT_ID = /^[0-9a-f-]{36}$/i;

export function parseView(raw: string | null): MapView | undefined {
  if (!raw) return undefined;
  const parts = raw.split(",").map(Number);
  if (parts.length < 3 || parts.some((n) => !Number.isFinite(n))) return undefined;
  const [lng, lat, zoom, bearing = 0, pitch = 0] = parts as [number, number, number, number?, number?];
  if (Math.abs(lng) > 180 || Math.abs(lat) > 90 || zoom < 0 || zoom > 22) return undefined;
  if (pitch < 0 || pitch > 85) return undefined;
  return { lng, lat, zoom, bearing: ((bearing % 360) + 360) % 360, pitch };
}

function parseList<T extends string>(raw: string | null, allowed: readonly T[]): T[] | undefined {
  if (raw === null) return undefined;
  const values = raw.split(",").filter((v): v is T => (allowed as readonly string[]).includes(v));
  // Nothing valid (typo, removed type): show everything rather than an empty map
  return values.length ? [...new Set(values)] : undefined;
}

export function parseMapUrlState(params: URLSearchParams): MapUrlState {
  const state: MapUrlState = {};
  const view = parseView(params.get("v"));
  if (view) state.view = view;
  const projection = params.get("p");
  if (projection === "2d") state.projection = "mercator";
  if (projection === "3d") state.projection = "globe";
  const basemap = params.get("b");
  if ((BASEMAPS as string[]).includes(basemap ?? "")) state.basemap = basemap as BasemapId;
  const types = parseList(params.get("t"), EVENT_TYPES as EventType[]);
  if (types) state.types = types;
  const severities = parseList(params.get("s"), ALL_SEVERITY_LEVELS);
  if (severities) state.severities = severities;
  const event = params.get("event");
  if (event && EVENT_ID.test(event)) state.event = event;
  const at = params.get("time");
  if (at && !Number.isNaN(Date.parse(at))) state.at = new Date(at).toISOString();
  return state;
}

const round = (n: number, digits: number) => Number(n.toFixed(digits));

/**
 * Serialize onto `base` (other params are kept). Values equal to the
 * defaults are removed so a fresh view has a clean URL.
 */
export function serializeMapUrlState(state: MapUrlState, base = new URLSearchParams()): string {
  const params = new URLSearchParams(base);
  const set = (key: string, value: string | undefined) =>
    value === undefined ? params.delete(key) : params.set(key, value);

  const v = state.view;
  set(
    "v",
    v &&
      [round(v.lng, 4), round(v.lat, 4), round(v.zoom, 2), round(v.bearing, 1), round(v.pitch, 1)]
        .join(",")
        .replace(/(,0)+$/, ""), // drop trailing zero bearing/pitch
  );
  set("p", state.projection === "mercator" ? "2d" : undefined);
  set("b", state.basemap && state.basemap !== "dark" ? state.basemap : undefined);
  const allTypes = !state.types || state.types.length === EVENT_TYPES.length;
  set("t", allTypes ? undefined : state.types!.join(","));
  const allSeverities = !state.severities || state.severities.length === ALL_SEVERITY_LEVELS.length;
  set("s", allSeverities ? undefined : state.severities!.join(","));
  set("event", state.event);
  // Hour precision is enough for a timeline position
  set("time", state.at?.slice(0, 13).concat(":00Z"));
  // Commas are legal in a query string; keep shared links readable
  return params.toString().replace(/%2C/gi, ",").replace(/%3A/gi, ":");
}
