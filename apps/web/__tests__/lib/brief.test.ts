import { describe, expect, it } from "vitest";
import type { ApiDisasterEvent } from "@/lib/api/client";
import { briefFromEvent, decodeBrief, encodeBrief, MAX_SCENES, type Brief } from "@/lib/brief";

const CAPTIONS = { before: "Before {title}", onset: "{title} begins", now: "Now", context: "At risk" };

const quake = {
  id: "0b6f7c2e-7d1a-4c6e-9d57-1f0a3c1b2e4d",
  type: "earthquake",
  title: "M 6.1 - Test",
  location: { lat: 35.7, lng: 139.7 },
  displayPoint: null,
  severity: "high",
  startDate: "2026-09-20T12:00:00Z",
  endDate: null,
  isActive: true,
  sources: [],
  createdAt: "2026-09-20T12:05:00Z",
  updatedAt: "2026-09-20T12:05:00Z",
} as unknown as ApiDisasterEvent;

describe("briefFromEvent", () => {
  it("tells before, onset, now and context around the event", () => {
    const brief = briefFromEvent(quake, CAPTIONS)!;
    expect(brief.eventId).toBe(quake.id);
    expect(brief.scenes.map((s) => s.caption)).toEqual(["Before M 6.1 - Test", "M 6.1 - Test begins", "Now", "At risk"]);
    expect(brief.scenes[0]!.at).toBe("2026-09-19T12:00:00.000Z");
    expect(brief.scenes[1]!.at).toBe("2026-09-20T13:00:00.000Z");
    expect(brief.scenes[2]!.at).toBeNull(); // ongoing: live
    expect(brief.scenes[1]!.layers).toEqual(["shakemaps"]);
    expect(brief.scenes[3]!.layers).toEqual(expect.arrayContaining(["shakemaps", "dams", "power-plants"]));
    expect(brief.scenes.every((s) => s.view.lat === 35.7 && s.view.lng === 139.7)).toBe(true);
  });

  it("ends at the event's end date when it is over", () => {
    const brief = briefFromEvent({ ...quake, endDate: "2026-09-21T00:00:00Z" }, CAPTIONS)!;
    expect(brief.scenes[3]!.at).toBe("2026-09-21T00:00:00Z");
  });

  it("needs a position", () => {
    const nowhere = { ...quake, location: { lat: null, lng: null } } as unknown as ApiDisasterEvent;
    expect(briefFromEvent(nowhere, CAPTIONS)).toBeNull();
  });
});

describe("encodeBrief / decodeBrief", () => {
  it("round-trips, including non-ASCII captions", () => {
    const brief = briefFromEvent({ ...quake, title: "도쿄 지진 — 震度" }, CAPTIONS)!;
    expect(decodeBrief(encodeBrief(brief))).toEqual(brief);
  });

  it("is URL-safe", () => {
    expect(encodeBrief(briefFromEvent(quake, CAPTIONS)!)).toMatch(/^[A-Za-z0-9_-]+$/);
  });

  it("rejects malformed input", () => {
    expect(decodeBrief(null)).toBeNull();
    expect(decodeBrief("not base64 !!")).toBeNull();
    expect(decodeBrief(btoa("[1,2]"))).toBeNull();
    expect(decodeBrief(btoa(JSON.stringify({ t: "x", s: [] })))).toBeNull();
  });

  it("drops unknown layers, bad scenes and clamps values", () => {
    const hostile = {
      t: "x".repeat(500),
      e: "../../admin",
      s: [
        { c: "ok", v: "10,20,5", a: "not a date", l: ["fires", "javascript:alert(1)", "fires"], d: 1e9 },
        { c: "bad view", v: "999,0,5" },
        ...Array.from({ length: 20 }, () => ({ c: "more", v: "0,0,2" })),
      ],
    };
    const brief = decodeBrief(btoa(JSON.stringify(hostile)).replace(/=+$/, "")) as Brief;
    expect(brief.title).toHaveLength(120);
    expect(brief.eventId).toBeUndefined();
    expect(brief.scenes).toHaveLength(MAX_SCENES - 1); // the bad view is dropped
    expect(brief.scenes[0]).toMatchObject({ at: null, layers: ["fires"], durationMs: 30_000 });
  });
});
