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

const KEYED_LAYERS = ["vessels"];

describe("layer registry", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("every layer declares provenance; only known layers need a server key", () => {
    for (const layer of LAYER_DEFINITIONS) {
      expect(layer.source.name, layer.id).toBeTruthy();
      expect(layer.source.license, layer.id).toBeTruthy();
      expect(layer.source.attribution, layer.id).toBeTruthy();
      expect(typeof layer.source.commercialUse, layer.id).toBe("boolean");
      // Keys are upgrades, not gates: a new keyed layer must be a deliberate choice
      expect(layer.auth === "keyless" || KEYED_LAYERS.includes(layer.id), layer.id).toBe(true);
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

  it("infrastructure layers query the viewport and hospitals reuse the basemap", () => {
    const plants = LAYER_DEFINITIONS_BY_ID.get("power-plants")!;
    const dams = LAYER_DEFINITIONS_BY_ID.get("dams")!;
    const hospitals = LAYER_DEFINITIONS_BY_ID.get("hospitals")!;
    for (const layer of [plants, dams]) {
      if (layer.kind !== "geojson") throw new Error("expected geojson");
      expect(layer.viewportDriven).toBe(true);
      expect(layer.minZoom).toBeGreaterThan(0); // never fetch 76k assets for the globe
    }
    expect(hospitals.kind).toBe("style");
  });

  it("infrastructure requests carry the viewport bbox and kind", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ type: "FeatureCollection", features: [] }) });
    vi.stubGlobal("fetch", fetchMock);
    const plants = LAYER_DEFINITIONS_BY_ID.get("power-plants")!;
    if (plants.kind !== "geojson") throw new Error("expected geojson");
    await plants.loadData({ bbox: [170, -30, -170, 0], zoom: 5 });
    const url = new URL(fetchMock.mock.calls[0]![0] as string);
    expect(Object.fromEntries(url.searchParams)).toMatchObject({
      min_lng: "170", max_lng: "-170", min_lat: "-30", max_lat: "0", kinds: "power_plant",
    });
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
