import { describe, expect, it } from "vitest";
import { matchArea, newAlerts, type WatchArea } from "@/lib/alerts";

const area: WatchArea = {
  id: "a",
  name: "Home",
  lat: 37.5,
  lng: 127,
  radiusKm: 100,
  minSeverity: "high",
  since: "2026-11-01T00:00:00Z",
};

const ev = (over: Record<string, unknown> = {}) => ({
  id: "e1",
  severity: "high" as const,
  isActive: true,
  createdAt: "2026-11-01T06:00:00Z",
  location: { lat: 37.6, lng: 127.1 },
  displayPoint: null,
  ...over,
});

describe("matchArea", () => {
  it("matches a nearby event at or above the minimum severity", () => {
    expect(matchArea(ev(), area)).toBeLessThan(20);
    expect(matchArea(ev({ severity: "critical" }), area)).not.toBeNull();
  });
  it("ignores weaker, distant, inactive or unplaced events", () => {
    expect(matchArea(ev({ severity: "medium" }), area)).toBeNull();
    expect(
      matchArea(ev({ location: { lat: 35.1, lng: 129 } }), area),
    ).toBeNull();
    expect(matchArea(ev({ isActive: false }), area)).toBeNull();
    expect(
      matchArea(ev({ location: { lat: null, lng: null } }), area),
    ).toBeNull();
  });
});

describe("newAlerts", () => {
  it("only alerts once, and only for events after the area was set up", () => {
    const events = [ev(), ev({ id: "old", createdAt: "2026-10-30T00:00:00Z" })];
    const first = newAlerts(events, [area], new Set());
    expect(first.map((h) => h.eventId)).toEqual(["e1"]);
    expect(newAlerts(events, [area], new Set(["a:e1"]))).toEqual([]);
  });
});
