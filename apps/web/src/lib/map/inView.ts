import type { ApiDisasterEvent, SeverityLevel } from "@/lib/api/client";
import { getEventPosition } from "@/lib/eventPosition";
import { SEVERITY_RANK } from "@/lib/map/eventLayers";

/** [west, south, east, north]; west > east crosses the antimeridian */
export type Bbox = [number, number, number, number];

export function inBbox(lat: number, lng: number, [west, south, east, north]: Bbox): boolean {
  if (lat < south || lat > north) return false;
  return west <= east ? lng >= west && lng <= east : lng >= west || lng <= east;
}

/**
 * Active events inside the view, most severe first, then newest: the list
 * behind the "in view" figure (UX plan 5.1).
 */
export function eventsInView(events: ApiDisasterEvent[], bbox: Bbox): ApiDisasterEvent[] {
  return events
    .filter((event) => {
      if (!event.isActive) return false;
      const position = getEventPosition(event);
      return position !== null && inBbox(position.lat, position.lng, bbox);
    })
    .sort(
      (a, b) =>
        (SEVERITY_RANK[b.severity as SeverityLevel] ?? 0) - (SEVERITY_RANK[a.severity as SeverityLevel] ?? 0) ||
        Date.parse(b.startDate) - Date.parse(a.startDate),
    );
}
