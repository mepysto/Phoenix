import { describe, expect, it, vi } from "vitest";
import { applyBasemap, BASEMAP_LAYERS, createBasemapStyle } from "@/lib/map/basemaps";

describe("basemaps", () => {
  it("uses only keyless tile hosts", () => {
    const style = createBasemapStyle("dark");
    const urls = Object.values(style.sources).flatMap((s) =>
      "tiles" in s && s.tiles ? s.tiles : [],
    );
    expect(urls.length).toBeGreaterThan(0);
    for (const url of urls) {
      expect(url).not.toMatch(/cartocdn|api[_-]?key|access_token/i);
    }
  });

  it("shows only the active basemap's layers", () => {
    const style = createBasemapStyle("satellite");
    const visible = style.layers
      .filter((l) => l.layout && "visibility" in l.layout && l.layout.visibility === "visible")
      .map((l) => l.id);
    expect(visible).toEqual(BASEMAP_LAYERS.satellite.map((l) => l.id));
  });

  it("switches every layer of a multi-layer basemap on a live map", () => {
    const map = { getLayer: vi.fn(() => ({})), setLayoutProperty: vi.fn() };
    applyBasemap(map, "dark");
    const calls = Object.fromEntries(map.setLayoutProperty.mock.calls.map(([id, , v]) => [id, v]));
    expect(calls).toEqual({
      "dark-basemap": "visible",
      "dark-labels": "visible",
      "satellite-basemap": "none",
    });
  });
});
