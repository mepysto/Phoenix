import { describe, expect, it } from "vitest";
import { bboxCenter, bboxRadiusKm, haversineKm } from "@/lib/map/geo";

describe("geo helpers", () => {
  it("measures great-circle distance", () => {
    // Tokyo -> Osaka is about 400 km
    expect(haversineKm({ lat: 35.68, lng: 139.76 }, { lat: 34.69, lng: 135.5 })).toBeCloseTo(400, -1);
    expect(haversineKm({ lat: 0, lng: 0 }, { lat: 0, lng: 0 })).toBe(0);
  });

  it("finds the centre of a bbox, across the antimeridian too", () => {
    expect(bboxCenter([120, 20, 150, 50])).toEqual({ lat: 35, lng: 135 });
    expect(bboxCenter([170, -30, -170, 0]).lng).toBeCloseTo(-180, 6);
  });

  it("covers the corners of a view", () => {
    const radius = bboxRadiusKm([139, 35, 141, 37]);
    expect(radius).toBeGreaterThan(130);
    expect(radius).toBeLessThan(160);
  });
});
