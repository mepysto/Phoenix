/**
 * Ring animation for events that just arrived from live updates. A pure
 * function of time so it is cheap to drive per frame and easy to test.
 */

/** One expansion of the ring */
export const PULSE_PERIOD_MS = 1600;
/** How far the ring grows beyond the marker, in pixels */
const PULSE_GROWTH_PX = 14;

export interface PulseFrame {
  /** Pixels added to the marker radius */
  grow: number;
  /** Ring stroke opacity */
  opacity: number;
}

/** Ring state at time t; reduced motion gets a still, clearly visible ring */
export function pulseFrame(t: number, reducedMotion: boolean): PulseFrame {
  if (reducedMotion) return { grow: 6, opacity: 0.9 };
  const phase = (((t % PULSE_PERIOD_MS) + PULSE_PERIOD_MS) % PULSE_PERIOD_MS) / PULSE_PERIOD_MS;
  return { grow: 4 + phase * PULSE_GROWTH_PX, opacity: 0.9 * (1 - phase) };
}
