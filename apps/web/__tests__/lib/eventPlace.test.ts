import { describe, expect, it } from "vitest";
import type { ApiDisasterEvent } from "@/lib/api/client";
import { placeName } from "@/lib/eventPlace";

const event = (title: string, location: Partial<ApiDisasterEvent["location"]> = {}) =>
  ({
    title,
    location: { lat: -23.94, lng: -66.76, country: null, countryCode: null, region: null, ...location },
    displayPoint: { lat: -23.94, lng: -66.76, source: "event" },
  }) as unknown as ApiDisasterEvent;

describe("placeName", () => {
  it("prefers the country, then the region", () => {
    expect(placeName(event("Flood", { country: "Mozambique", region: "Gaza" }))).toBe("Mozambique");
    expect(placeName(event("Flood", { region: "Gaza" }))).toBe("Gaza");
  });

  it("reads the place out of USGS titles", () => {
    expect(placeName(event("M 4.7 - 54 km NW of San Antonio de los Cobres, Argentina"))).toBe(
      "San Antonio de los Cobres, Argentina",
    );
    expect(placeName(event("M 5.2 - off the west coast of northern Sumatra"))).toBe("northern Sumatra");
    expect(placeName(event("M 4.5 - Fiji region"))).toBe("Fiji region");
  });

  it("reads 'X in Y' titles", () => {
    expect(placeName(event("Flood in Mozambique and South Africa"))).toBe("Mozambique and South Africa");
  });

  it("falls back to coordinates", () => {
    expect(placeName(event("Iceberg C39"))).toMatch(/23\.94.*66\.76/);
  });
});
