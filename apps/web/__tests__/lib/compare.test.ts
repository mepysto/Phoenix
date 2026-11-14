import { describe, expect, it } from "vitest";
import {
  compareTileUrl,
  compareReady,
  defaultCompareDates,
  tileCoords,
  tileGrid,
} from "@/lib/compare";

describe("tileCoords", () => {
  it("puts the origin at the centre of the world", () => {
    expect(tileCoords(0, 0, 1)).toEqual({ x: 1, y: 1 });
  });
});

describe("tileGrid", () => {
  it("returns nine tiles with the point inside the centre tile", () => {
    const grid = tileGrid(37.5, 127, 8);
    expect(grid.tiles).toHaveLength(9);
    expect(grid.focus.x).toBeGreaterThanOrEqual(256);
    expect(grid.focus.x).toBeLessThan(512);
    expect(grid.focus.y).toBeGreaterThanOrEqual(256);
    expect(grid.focus.y).toBeLessThan(512);
  });

  it("wraps x across the antimeridian", () => {
    const grid = tileGrid(0, 179.9, 3);
    const xs = grid.tiles.filter((t) => t.row === 0).map((t) => t.x);
    expect(xs).toEqual([6, 7, 0]);
  });

  it("keeps rows inside the world near the poles", () => {
    const grid = tileGrid(85, 0, 3);
    expect(Math.min(...grid.tiles.map((t) => t.y))).toBe(0);
  });
});

describe("defaultCompareDates", () => {
  it("compares a week before onset with two days after it", () => {
    const d = defaultCompareDates(
      new Date("2026-03-10T05:00:00Z"),
      new Date("2026-04-01T00:00:00Z"),
    );
    expect(d).toEqual({ before: "2026-03-03", after: "2026-03-12" });
  });

  it("never asks for mosaics that are still being assembled", () => {
    const d = defaultCompareDates(
      new Date("2026-03-10T05:00:00Z"),
      new Date("2026-03-12T08:00:00Z"),
    );
    expect(d.after).toBe("2026-03-10");
  });
});

describe("compareReady", () => {
  it("waits until imagery after onset can exist", () => {
    const start = new Date("2026-03-10T05:00:00Z");
    expect(compareReady(start, new Date("2026-03-11T05:00:00Z"))).toBe(false);
    expect(compareReady(start, new Date("2026-03-12T06:00:00Z"))).toBe(true);
  });
});

it("builds a GIBS tile URL", () => {
  expect(compareTileUrl("2026-03-09", 8, { x: 1, y: 2 })).toMatch(
    /VIIRS_SNPP_CorrectedReflectance_TrueColor\/default\/2026-03-09\/GoogleMapsCompatible_Level9\/8\/2\/1\.jpg$/,
  );
});
