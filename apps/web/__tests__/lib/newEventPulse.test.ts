import { describe, expect, it } from "vitest";
import { PULSE_PERIOD_MS, pulseFrame } from "@/lib/map/newEventPulse";

describe("pulseFrame", () => {
  it("is a pure function of time that repeats every period", () => {
    expect(pulseFrame(300, false)).toEqual(pulseFrame(300 + PULSE_PERIOD_MS, false));
    expect(pulseFrame(-200, false)).toEqual(pulseFrame(PULSE_PERIOD_MS - 200, false));
  });

  it("grows and fades over one period", () => {
    const start = pulseFrame(0, false);
    const late = pulseFrame(PULSE_PERIOD_MS * 0.9, false);
    expect(late.grow).toBeGreaterThan(start.grow);
    expect(late.opacity).toBeLessThan(start.opacity);
  });

  it("holds a still, visible ring for reduced motion", () => {
    expect(pulseFrame(0, true)).toEqual(pulseFrame(777, true));
    expect(pulseFrame(0, true).opacity).toBeGreaterThan(0.5);
  });
});
