import { afterEach, describe, expect, it, vi } from "vitest";
import {
  ALL_LAYER_DEFINITIONS,
  availableLayers,
  LAYER_DEFINITIONS,
  LAYER_DEFINITIONS_BY_ID,
  type RasterLayerDefinition,
} from "@/lib/layers/registry";

const radar = LAYER_DEFINITIONS_BY_ID.get("radar") as RasterLayerDefinition;
const clouds = LAYER_DEFINITIONS_BY_ID.get("clouds-infrared") as RasterLayerDefinition;

describe("layer registry", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("every layer declares provenance and is keyless for now", () => {
    for (const layer of LAYER_DEFINITIONS) {
      expect(layer.source.name, layer.id).toBeTruthy();
      expect(layer.source.license, layer.id).toBeTruthy();
      expect(layer.source.attribution, layer.id).toBeTruthy();
      expect(typeof layer.source.commercialUse, layer.id).toBe("boolean");
      expect(layer.auth, layer.id).toBe("keyless");
    }
    expect(new Set(LAYER_DEFINITIONS.map((l) => l.id)).size).toBe(LAYER_DEFINITIONS.length);
  });

  it("commercial deployments drop non-commercial-only sources (RainViewer)", () => {
    const ids = (commercial: boolean) =>
      availableLayers(ALL_LAYER_DEFINITIONS, commercial).map((d) => d.id);
    expect(ids(false)).toContain("radar");
    expect(ids(true)).not.toContain("radar");
    expect(ids(true)).toContain("clouds-infrared");
  });

  it("radar attribution links to RainViewer as its terms require", () => {
    expect(radar.source.attribution).toContain('href="https://www.rainviewer.com/"');
  });

  it("cyclone layer draws cone, tracks, positions and a label for the current position", () => {
    const cyclones = LAYER_DEFINITIONS_BY_ID.get("cyclones")!;
    expect(cyclones.kind).toBe("geojson");
    if (cyclones.kind !== "geojson") return;
    const layers = cyclones.styleLayers("overlay-cyclones");
    expect(layers.map((l) => l.type)).toEqual(["fill", "line", "line", "line", "circle", "symbol"]);
    expect(layers.every((l) => "source" in l && l.source === "overlay-cyclones")).toBe(true);
    expect(new Set(layers.map((l) => l.id)).size).toBe(layers.length);
  });

  it("ShakeMap labels only whole-intensity contours", () => {
    const shakemaps = LAYER_DEFINITIONS_BY_ID.get("shakemaps")!;
    if (shakemaps.kind !== "geojson") throw new Error("expected geojson layer");
    const [lines, labels] = shakemaps.styleLayers("overlay-shakemaps");
    expect(lines!.type).toBe("line");
    expect(labels!.type).toBe("symbol");
    expect((labels as { filter?: unknown }).filter).toEqual(["==", ["%", ["get", "mmi"], 1], 0]);
  });

  it("radar uses the newest RainViewer frame", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          host: "https://tilecache.rainviewer.com",
          radar: { past: [{ path: "/v2/radar/old" }, { path: "/v2/radar/newest" }] },
        }),
      }),
    );
    const { tiles } = await radar.resolveTiles(new Date());
    expect(tiles[0]).toBe(
      "https://tilecache.rainviewer.com/v2/radar/newest/256/{z}/{x}/{y}/2/1_1.png",
    );
  });

  it("radar reports an error instead of producing broken tile URLs", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 503 }));
    await expect(radar.resolveTiles(new Date())).rejects.toThrow("503");
  });

  it("GOES tiles refresh every 10 minutes but cache within the window", async () => {
    const t0 = new Date("2026-09-24T10:00:00Z");
    const [a] = (await clouds.resolveTiles(t0)).tiles;
    const [b] = (await clouds.resolveTiles(new Date("2026-09-24T10:09:00Z"))).tiles;
    const [c] = (await clouds.resolveTiles(new Date("2026-09-24T10:10:00Z"))).tiles;
    expect(a).toBe(b);
    expect(c).not.toBe(a);
  });
});
