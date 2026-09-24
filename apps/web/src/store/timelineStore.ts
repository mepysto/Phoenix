import { create } from "zustand";

export const PLAYBACK_SPEEDS = [0.25, 0.5, 1, 2, 4] as const;
export type PlaybackSpeed = (typeof PLAYBACK_SPEEDS)[number];

interface TimelineState {
  /** ISO instant being viewed; null = live (now) */
  at: string | null;
  playing: boolean;
  speed: PlaybackSpeed;
  setAt: (at: string | null) => void;
  setPlaying: (playing: boolean) => void;
  cycleSpeed: () => void;
}

export const useTimelineStore = create<TimelineState>()((set, get) => ({
  at: null,
  playing: false,
  speed: 1,
  // Returning to live also stops playback
  setAt: (at) => set(at === null ? { at, playing: false } : { at }),
  setPlaying: (playing) => set({ playing }),
  cycleSpeed: () => {
    const index = PLAYBACK_SPEEDS.indexOf(get().speed);
    set({ speed: PLAYBACK_SPEEDS[(index + 1) % PLAYBACK_SPEEDS.length]! });
  },
}));
