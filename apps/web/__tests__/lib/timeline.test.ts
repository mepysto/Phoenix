import { describe, expect, it } from "vitest";
import { instantAt, nextPlaybackInstant, positionOf, timelineWindow, WINDOW_DAYS } from "@/lib/timeline";

const NOW = new Date("2026-09-24T13:37:00Z");
const win = timelineWindow(NOW);

describe("timeline maths", () => {
  it("spans the last 30 days from a UTC midnight", () => {
    expect(win.start.toISOString()).toBe("2026-08-25T00:00:00.000Z");
    expect(win.hours).toBe(WINDOW_DAYS * 24 + 13);
  });

  it("maps live to the end and past instants to hour positions", () => {
    expect(positionOf(win, null)).toBe(win.hours);
    expect(positionOf(win, "2026-08-26T06:00:00Z")).toBe(30);
    expect(positionOf(win, "2020-01-01T00:00:00Z")).toBe(0); // clamped
  });

  it("round-trips positions; the last position means live", () => {
    expect(instantAt(win, 30)).toBe("2026-08-26T06:00:00.000Z");
    expect(instantAt(win, win.hours)).toBeNull();
  });

  it("playback steps by speed and ends back at live", () => {
    expect(nextPlaybackInstant(win, "2026-08-26T06:00:00.000Z", 1)).toBe("2026-08-26T09:00:00.000Z");
    expect(nextPlaybackInstant(win, "2026-08-26T06:00:00.000Z", 4)).toBe("2026-08-26T18:00:00.000Z");
    // 0.25x still moves at least one hour
    expect(nextPlaybackInstant(win, "2026-08-26T06:00:00.000Z", 0.25)).toBe("2026-08-26T07:00:00.000Z");
    expect(nextPlaybackInstant(win, instantAt(win, win.hours - 1), 1)).toBeNull();
  });
});
