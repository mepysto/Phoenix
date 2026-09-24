import { describe, expect, it } from "vitest";
import { formatPosition, getEventPosition } from "@/lib/eventPosition";

describe("getEventPosition", () => {
  it("prefers the API display point (e.g. a country centroid)", () => {
    expect(
      getEventPosition({
        location: { lat: null, lng: null },
        displayPoint: { lat: 36.2, lng: 138.2, source: "country_centroid" },
      }),
    ).toEqual({ lat: 36.2, lng: 138.2 });
  });

  it("falls back to raw coordinates, keeping 0/0 as valid", () => {
    expect(getEventPosition({ location: { lat: 0, lng: 0 }, displayPoint: null })).toEqual({
      lat: 0,
      lng: 0,
    });
  });

  it("returns null when the event cannot be placed", () => {
    expect(getEventPosition({ location: { lat: null, lng: 10 }, displayPoint: null })).toBeNull();
    expect(formatPosition(null)).toBe("—");
  });
});
