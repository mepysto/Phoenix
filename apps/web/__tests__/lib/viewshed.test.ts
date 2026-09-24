import { describe, expect, it } from "vitest";
import { directionBearing, wedge, withViewsheds } from "@/lib/map/viewshed";

describe("camera viewsheds", () => {
  it("maps compass directions", () => {
    expect(directionBearing("North")).toBe(0);
    expect(directionBearing(" west ")).toBe(270);
    expect(directionBearing("Median")).toBeNull();
    expect(directionBearing(null)).toBeNull();
  });

  it("builds a closed wedge pointing the right way", () => {
    const ring = wedge(0, 0, 90).coordinates[0]!;
    expect(ring[0]).toEqual([0, 0]);
    expect(ring[ring.length - 1]).toEqual([0, 0]);
    // Eastward: every arc point is east of the camera, about 300 m out
    for (const [lng] of ring.slice(1, -1)) expect(lng).toBeGreaterThan(0.0023);
  });

  it("adds wedges only for cameras with a direction", () => {
    const cameras: GeoJSON.FeatureCollection = {
      type: "FeatureCollection",
      features: [
        { type: "Feature", geometry: { type: "Point", coordinates: [-122.27, 37.82] }, properties: { direction: "North" } },
        { type: "Feature", geometry: { type: "Point", coordinates: [-122.2, 37.8] }, properties: { direction: "" } },
      ],
    };
    const result = withViewsheds(cameras);
    expect(result.features.map((f) => f.properties?.kind ?? "camera")).toEqual(["viewshed", "camera", "camera"]);
  });
});
