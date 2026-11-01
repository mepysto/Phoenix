/**
 * Watch areas: tell me when a disaster appears near a place I care about.
 *
 * Runs in the browser while Phoenix is open (the live WebSocket feeds the
 * event store). Nothing about the areas leaves the device.
 */

import type { ApiDisasterEvent, SeverityLevel } from "@/lib/api/client";
import { getEventPosition } from "@/lib/eventPosition";

export interface WatchArea {
  id: string;
  name: string;
  lat: number;
  lng: number;
  radiusKm: number;
  minSeverity: SeverityLevel;
  /** Only events created after this instant alert (ISO) */
  since: string;
}

export const SEVERITY_RANK: Record<SeverityLevel, number> = {
  low: 0,
  medium: 1,
  high: 2,
  critical: 3,
};

export const RADIUS_CHOICES = [50, 100, 250, 500, 1000] as const;

export function distanceKm(
  a: { lat: number; lng: number },
  b: { lat: number; lng: number },
): number {
  const p1 = (a.lat * Math.PI) / 180;
  const p2 = (b.lat * Math.PI) / 180;
  const dl = ((b.lng - a.lng) * Math.PI) / 180;
  const h =
    Math.sin((p2 - p1) / 2) ** 2 +
    Math.cos(p1) * Math.cos(p2) * Math.sin(dl / 2) ** 2;
  return 2 * 6371 * Math.asin(Math.sqrt(Math.min(1, h)));
}

type AlertEvent = Pick<
  ApiDisasterEvent,
  "id" | "severity" | "createdAt" | "location" | "displayPoint" | "isActive"
>;

/** Distance in km when the event falls inside the area, otherwise null */
export function matchArea(event: AlertEvent, area: WatchArea): number | null {
  if (!event.isActive) return null;
  if (
    SEVERITY_RANK[event.severity as SeverityLevel] <
    SEVERITY_RANK[area.minSeverity]
  )
    return null;
  const pos = getEventPosition(event);
  if (!pos) return null;
  const d = distanceKm(pos, area);
  return d <= area.radiusKm ? d : null;
}

export interface AlertHit {
  eventId: string;
  areaId: string;
  distanceKm: number;
}

/**
 * New alerts: matching events created after the area was set up and not
 * already notified. `seen` holds "areaId:eventId" keys.
 */
export function newAlerts(
  events: AlertEvent[],
  areas: WatchArea[],
  seen: ReadonlySet<string>,
): AlertHit[] {
  const hits: AlertHit[] = [];
  for (const area of areas) {
    const since = Date.parse(area.since);
    for (const e of events) {
      if (seen.has(`${area.id}:${e.id}`)) continue;
      if (Date.parse(e.createdAt) <= since) continue;
      const d = matchArea(e, area);
      if (d !== null)
        hits.push({ eventId: e.id, areaId: area.id, distanceKm: d });
    }
  }
  return hits;
}
