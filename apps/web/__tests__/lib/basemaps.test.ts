import { describe, expect, it, vi } from "vitest";
import type { LayerSpecification } from "maplibre-gl";
import {
  applyBasemap,
  loadBasemapStyle,
  SATELLITE_LAYER_ID,
  SATELLITE_SOURCE,
} from "@/lib/map/basemaps";

const vectorStyle = {
  version: 8,
  glyphs: "https://tiles.openfreemap.org/fonts/{fontstack}/{range}.pbf",
  sources: { openmaptiles: { type: "vector", url: "https://tiles.openfreemap.org/planet" } },
  layers: [
    { id: "background", type: "background" },
    { id: "water", type: "fill", source: "openmaptiles", "source-layer": "water" },
    { id: "place-label", type: "symbol", source: "openmaptiles", "source-layer": "place" },
  ],
};
const okFetch = vi.fn(async () => ({ ok: true, json: async () => structuredClone(vectorStyle) }));
const visibility = (layers: LayerSpecification[]) =>
  Object.fromEntries(layers.map((l) => [l.id, (l.layout as { visibility?: string }).visibility]));

describe("basemaps", () => {
  it("uses licence-verified hosts only (no Esri/CARTO, no keys)", () => {
    for (const url of SATELLITE_SOURCE.tiles ?? []) {
      expect(url).not.toMatch(/arcgisonline|cartocdn|api[_-]?key|access_token/i);
    }
  });

  it("dark: vector style visible, satellite hidden", async () => {
    const style = await loadBasemapStyle("dark", okFetch as never);
    expect(visibility(style.layers)).toEqual({
      [SATELLITE_LAYER_ID]: "none",
      background: "visible",
      water: "visible",
      "place-label": "visible",
    });
    expect(style.layers[0]!.id).toBe(SATELLITE_LAYER_ID); // imagery below labels
  });

  it("satellite: imagery with the vector labels kept on top (hybrid)", async () => {
    const style = await loadBasemapStyle("satellite", okFetch as never);
    expect(visibility(style.layers)).toEqual({
      [SATELLITE_LAYER_ID]: "visible",
      background: "none",
      water: "none",
      "place-label": "visible",
    });
  });

  it("falls back to a working satellite map when the vector style is unreachable", async () => {
    const warn = vi.spyOn(console, "warn").mockImplementation(() => {});
    const style = await loadBasemapStyle("dark", vi.fn(async () => ({ ok: false, status: 503 })) as never);
    expect(visibility(style.layers)[SATELLITE_LAYER_ID]).toBe("visible");
    expect(style.glyphs).toBeTruthy(); // cluster labels still render
    warn.mockRestore();
  });

  it("applyBasemap only touches basemap layers, never overlays or events", async () => {
    const style = await loadBasemapStyle("dark", okFetch as never);
    const layers = [
      ...style.layers,
      { id: "overlay-radar", type: "raster", source: "x" },
      { id: "clusters", type: "circle", source: "events" },
    ] as LayerSpecification[];
    const map = { getStyle: () => ({ layers }), setLayoutProperty: vi.fn() };
    applyBasemap(map, "satellite");
    const touched = map.setLayoutProperty.mock.calls.map(([id]) => id);
    expect(touched).not.toContain("overlay-radar");
    expect(touched).not.toContain("clusters");
    expect(Object.fromEntries(map.setLayoutProperty.mock.calls.map(([id, , v]) => [id, v]))).toEqual({
      [SATELLITE_LAYER_ID]: "visible",
      background: "none",
      water: "none",
      "place-label": "visible",
    });
  });
});
