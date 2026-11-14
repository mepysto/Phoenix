import { describe, expect, it } from "vitest";
import { initialView, longitudeFromTimezone } from "@/lib/map/initialView";

describe("initial map view", () => {
  it("faces the reader's longitude from the time zone", () => {
    expect(longitudeFromTimezone(-540)).toBe(135); // UTC+9, Seoul
    expect(longitudeFromTimezone(0)).toBe(0);
    expect(longitudeFromTimezone(300)).toBe(-75); // UTC-5, New York
  });

  it("sizes the globe to most of the smaller side of the map", () => {
    const desktop = initialView(1152, 844, -540);
    // 85% of 844px at 140px per zoom-0 globe
    expect(desktop.zoom).toBeCloseTo(Math.log2((0.85 * 844) / 140), 1);
    expect(desktop.lng).toBe(135);
    // A phone is limited by its width, so the globe is smaller
    expect(initialView(390, 700, 0).zoom).toBeLessThan(desktop.zoom);
  });

  it("stays within sensible zoom bounds", () => {
    expect(initialView(10, 10).zoom).toBe(0.5);
    expect(initialView(10000, 10000).zoom).toBe(3);
  });
});
