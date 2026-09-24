import { describe, expect, it } from "vitest";
import { parseMapUrlState, serializeMapUrlState } from "@/lib/map/urlState";

const parse = (qs: string) => parseMapUrlState(new URLSearchParams(qs));

describe("map URL state", () => {
  it("keeps only known, non-default view modes", () => {
    expect(parse("m=nvg").mode).toBe("nvg");
    expect(parse("m=normal").mode).toBeUndefined();
    expect(parse("m=xray").mode).toBeUndefined();
    expect(serializeMapUrlState({ mode: "normal" })).toBe("");
  });

  it("round-trips a full state", () => {
    const state = {
      view: { lng: 139.6917, lat: 35.6895, zoom: 6.5, bearing: 30, pitch: 45 },
      projection: "mercator" as const,
      basemap: "satellite" as const,
      types: ["earthquake", "flood"] as const,
      severities: ["high", "critical"] as const,
      event: "661f99ef-07b4-4f39-9232-d5da4fb3c319",
      at: "2026-09-01T06:00:00.000Z", // must not collide with the types param "t"
      mode: "flir" as const,
    };
    const qs = serializeMapUrlState(state as never);
    expect(parse(qs)).toEqual(state);
  });

  it("omits defaults so the default view has a clean URL", () => {
    expect(
      serializeMapUrlState({ projection: "globe", basemap: "dark", types: undefined }),
    ).toBe("");
    expect(serializeMapUrlState({ view: { lng: 10, lat: 20, zoom: 3, bearing: 0, pitch: 0 } })).toBe(
      "v=10,20,3",
    );
  });

  it("drops invalid values instead of failing", () => {
    expect(parse("v=999,20,3&p=4d&b=neon&t=earthquake,alien&s=extreme&event=../../etc")).toEqual({
      types: ["earthquake"],
    });
    expect(parse("v=abc")).toEqual({});
  });

  it("keeps unrelated query params", () => {
    const qs = serializeMapUrlState({ basemap: "satellite" }, new URLSearchParams("utm=x"));
    expect(new URLSearchParams(qs).get("utm")).toBe("x");
  });

  it("carries the timeline instant at hour precision", () => {
    const qs = serializeMapUrlState({ at: "2026-09-01T06:42:10.000Z" });
    expect(qs).toBe("time=2026-09-01T06:00Z");
    expect(parse(qs).at).toBe("2026-09-01T06:00:00.000Z");
    expect(parse("time=not-a-date").at).toBeUndefined();
  });

  it("normalises bearing into 0..360", () => {
    expect(parse("v=0,0,2,-90").view?.bearing).toBe(270);
  });
});
