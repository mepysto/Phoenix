import { afterEach, describe, expect, it, vi } from "vitest";
import { LAYER_DEFINITIONS, LAYER_DEFINITIONS_BY_ID } from "@/lib/layers/registry";

const radar = LAYER_DEFINITIONS_BY_ID.get("radar")!;
const clouds = LAYER_DEFINITIONS_BY_ID.get("clouds-infrared")!;

describe("layer registry", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("every layer declares provenance and is keyless for now", () => {
    for (const layer of LAYER_DEFINITIONS) {
      expect(layer.source.name, layer.id).toBeTruthy();
      expect(layer.source.license, layer.id).toBeTruthy();
      expect(layer.source.attribution, layer.id).toBeTruthy();
      expect(layer.auth, layer.id).toBe("keyless");
    }
    expect(new Set(LAYER_DEFINITIONS.map((l) => l.id)).size).toBe(LAYER_DEFINITIONS.length);
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
