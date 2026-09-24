import { describe, expect, it } from "vitest";
import { nearbyRadiusKm } from "@/lib/viewSummary";

describe("nearbyRadiusKm", () => {
  it("shrinks with zoom within the API limits", () => {
    expect(nearbyRadiusKm(1)).toBe(5000);
    expect(nearbyRadiusKm(5)).toBe(1250);
    expect(nearbyRadiusKm(8)).toBe(156);
    expect(nearbyRadiusKm(18)).toBe(25);
  });
});
