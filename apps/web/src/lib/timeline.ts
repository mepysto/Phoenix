/** Time maths for the timeline scrubber (pure, UTC). */

export const WINDOW_DAYS = 30;
const HOUR = 3_600_000;
/** Playback advances this many hours per tick at 1x */
export const HOURS_PER_TICK = 3;
export const TICK_MS = 250;

export interface TimelineWindow {
  start: Date;
  end: Date;
  /** Number of hour steps between start and end */
  hours: number;
}

/** The last WINDOW_DAYS up to `now`, starting at a UTC midnight (aligns with day buckets) */
export function timelineWindow(now: Date): TimelineWindow {
  const start = new Date(now.getTime() - WINDOW_DAYS * 24 * HOUR);
  start.setUTCHours(0, 0, 0, 0);
  return { start, end: now, hours: Math.floor((now.getTime() - start.getTime()) / HOUR) };
}

/** Slider position (hours from start) for an instant; null (live) = the end */
export function positionOf(window: TimelineWindow, at: string | null): number {
  if (at === null) return window.hours;
  const hours = Math.round((Date.parse(at) - window.start.getTime()) / HOUR);
  return Math.min(Math.max(hours, 0), window.hours);
}

/** Instant for a slider position; the last position means live (null) */
export function instantAt(window: TimelineWindow, position: number): string | null {
  if (position >= window.hours) return null;
  return new Date(window.start.getTime() + position * HOUR).toISOString();
}

/** Next instant during playback; null once it reaches the present (back to live) */
export function nextPlaybackInstant(window: TimelineWindow, at: string | null, speed: number): string | null {
  const position = positionOf(window, at ?? window.start.toISOString());
  return instantAt(window, position + Math.max(1, Math.round(HOURS_PER_TICK * speed)));
}
