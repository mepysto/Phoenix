import { describe, expect, it } from "vitest";
import type { ApiDisasterEvent } from "@/lib/api/client";
import {
  SEVERITY_RANK,
  eventsToGeoJSON,
  getMarkerSize,
  severityColorExpression,
} from "@/lib/map/eventLayers";
import { eventTypeImageId } from "@/lib/map/markerIcons";

const event = (over: Partial<ApiDisasterEvent>): ApiDisasterEvent =>
  ({
    id: "e1",
    type: "flood",
    title: "Flood",
    description: null,
    severity: "high",
    isActive: true,
    location: { lat: 10, lng: 20, country: null, countryCode: null, region: null },
    displayPoint: { lat: 10, lng: 20, source: "event" },
    ...over,
  }) as unknown as ApiDisasterEvent;

const colors = { low: "#00f", medium: "#fa0", high: "#f00", critical: "#a0f" };

describe("event marker encoding (colour = severity, icon = type)", () => {
  it("carries the severity rank and the type icon on every point", () => {
    const fc = eventsToGeoJSON([
      event({ id: "a", type: "earthquake", severity: "critical" }),
      event({ id: "b", type: "flood", severity: "low" }),
    ]);

    const props = fc.features.map((f) => f.properties);
    expect(props[0]).toMatchObject({ sevRank: 3, icon: eventTypeImageId("earthquake") });
    expect(props[1]).toMatchObject({ sevRank: 0, icon: eventTypeImageId("flood") });
    // No per-type colour: the map paints colour from severity alone
    expect(props[0]).not.toHaveProperty("color");
  });

  it("maps each severity rank to its own colour, for points and clusters alike", () => {
    for (const property of ["sevRank", "maxSev"] as const) {
      const expr = severityColorExpression(property, colors);
      expect(expr.slice(0, 2)).toEqual(["match", ["get", property]]);
      const pairs = Object.fromEntries([[expr[2], expr[3]], [expr[4], expr[5]], [expr[6], expr[7]]]);
      expect(pairs).toEqual({
        [SEVERITY_RANK.critical]: colors.critical,
        [SEVERITY_RANK.high]: colors.high,
        [SEVERITY_RANK.medium]: colors.medium,
      });
      expect(expr[8]).toBe(colors.low); // fallback = low
    }
  });

  it("draws more severe markers larger", () => {
    expect(getMarkerSize("low")).toBeLessThan(getMarkerSize("medium"));
    expect(getMarkerSize("medium")).toBeLessThan(getMarkerSize("high"));
    expect(getMarkerSize("high")).toBeLessThan(getMarkerSize("critical"));
  });
});
