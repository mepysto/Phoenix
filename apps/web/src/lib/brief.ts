import type { ApiDisasterEvent } from "@/lib/api/client";
import { getEventPosition } from "@/lib/eventPosition";
import { LAYER_DEFINITIONS_BY_ID } from "@/lib/layers/registry";
import { parseView, type MapView } from "@/lib/map/urlState";

/**
 * Disaster Brief (G-3): a short story of one disaster told with the map.
 * Each scene sets the camera, the timeline instant and the overlays, with a
 * caption. Briefs travel in the URL (?brief=), so they need no accounts or
 * storage; decoding treats that input as untrusted.
 */
export interface BriefScene {
  caption: string;
  view: MapView;
  /** Timeline instant (ISO); null = live */
  at: string | null;
  /** Overlay layer ids to show (others are hidden while the brief plays) */
  layers: string[];
  durationMs: number;
}

export interface Brief {
  title: string;
  /** Event the brief is about (opens its card) */
  eventId?: string;
  scenes: BriefScene[];
}

export const MAX_SCENES = 12;
const MAX_TITLE = 120;
const MAX_CAPTION = 280;
const DEFAULT_DURATION_MS = 6000;
const HOUR_MS = 3_600_000;

/** Overlay that explains each hazard best */
const HAZARD_LAYER: Partial<Record<string, string>> = {
  earthquake: "shakemaps",
  hurricane: "cyclones",
  wildfire: "fires",
  storm: "cyclones", // EONET files tropical cyclones under severeStorms
  flood: "radar",
};

export interface BriefCaptions {
  before: string;
  onset: string;
  now: string;
  context: string;
}

/** A four-scene brief built from an event: before, onset, now, what is at risk */
export function briefFromEvent(event: ApiDisasterEvent, captions: BriefCaptions): Brief | null {
  const position = getEventPosition(event);
  if (!position) return null;
  const { lat, lng } = position;
  const hazard = HAZARD_LAYER[event.type];
  const hazardLayers = hazard && LAYER_DEFINITIONS_BY_ID.has(hazard) ? [hazard] : [];
  const infrastructure = ["dams", "power-plants"].filter((id) => LAYER_DEFINITIONS_BY_ID.has(id));
  const onset = Date.parse(event.startDate);
  const view = (zoom: number, pitch = 0): MapView => ({ lng, lat, zoom, bearing: 0, pitch });
  const fill = (text: string) => text.replace("{title}", event.title);

  return {
    title: event.title.slice(0, MAX_TITLE),
    eventId: event.id,
    scenes: [
      { caption: fill(captions.before), view: view(3), at: new Date(onset - 24 * HOUR_MS).toISOString(), layers: [], durationMs: DEFAULT_DURATION_MS },
      { caption: fill(captions.onset), view: view(5.5), at: new Date(onset + HOUR_MS).toISOString(), layers: hazardLayers, durationMs: DEFAULT_DURATION_MS },
      { caption: fill(captions.now), view: view(6.5, 30), at: event.endDate ?? null, layers: hazardLayers, durationMs: DEFAULT_DURATION_MS },
      { caption: fill(captions.context), view: view(8, 45), at: event.endDate ?? null, layers: [...hazardLayers, ...infrastructure], durationMs: DEFAULT_DURATION_MS },
    ],
  };
}

// --- URL encoding -----------------------------------------------------------

function toBase64Url(text: string): string {
  const bytes = new TextEncoder().encode(text);
  let binary = "";
  for (const b of bytes) binary += String.fromCharCode(b);
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function fromBase64Url(encoded: string): string {
  const binary = atob(encoded.replace(/-/g, "+").replace(/_/g, "/"));
  return new TextDecoder().decode(Uint8Array.from(binary, (c) => c.charCodeAt(0)));
}

/** Compact form: the view is stored as the same "lng,lat,zoom,bearing,pitch" string as ?v= */
export function encodeBrief(brief: Brief): string {
  return toBase64Url(
    JSON.stringify({
      t: brief.title,
      e: brief.eventId,
      s: brief.scenes.map((s) => ({
        c: s.caption,
        v: [s.view.lng, s.view.lat, s.view.zoom, s.view.bearing, s.view.pitch].map((n) => +n.toFixed(4)).join(","),
        a: s.at,
        l: s.layers,
        d: s.durationMs,
      })),
    }),
  );
}

const EVENT_ID = /^[0-9a-f-]{36}$/i;

function text(value: unknown, max: number): string | null {
  return typeof value === "string" ? value.slice(0, max) : null;
}

/** Parse ?brief=; null for anything malformed. Unknown layers and bad scenes are dropped. */
export function decodeBrief(encoded: string | null): Brief | null {
  if (!encoded || encoded.length > 16_000) return null;
  let raw: unknown;
  try {
    raw = JSON.parse(fromBase64Url(encoded));
  } catch {
    return null;
  }
  if (typeof raw !== "object" || raw === null) return null;
  const { t, e, s } = raw as Record<string, unknown>;
  const title = text(t, MAX_TITLE);
  if (!title || !Array.isArray(s)) return null;

  const scenes: BriefScene[] = [];
  for (const item of s.slice(0, MAX_SCENES)) {
    if (typeof item !== "object" || item === null) continue;
    const { c, v, a, l, d } = item as Record<string, unknown>;
    const view = parseView(typeof v === "string" ? v : null);
    if (!view) continue;
    const at = typeof a === "string" && !Number.isNaN(Date.parse(a)) ? new Date(a).toISOString() : null;
    scenes.push({
      caption: text(c, MAX_CAPTION) ?? "",
      view,
      at,
      layers: Array.isArray(l)
        ? [...new Set(l.filter((id): id is string => typeof id === "string" && LAYER_DEFINITIONS_BY_ID.has(id)))]
        : [],
      durationMs:
        typeof d === "number" && Number.isFinite(d) ? Math.min(30_000, Math.max(2000, d)) : DEFAULT_DURATION_MS,
    });
  }
  if (!scenes.length) return null;
  return { title, eventId: typeof e === "string" && EVENT_ID.test(e) ? e : undefined, scenes };
}
