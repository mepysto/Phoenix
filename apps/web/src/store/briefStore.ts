import { create } from "zustand";
import type { Brief } from "@/lib/brief";

interface BriefState {
  brief: Brief | null;
  index: number;
  playing: boolean;
  start: (brief: Brief) => void;
  goTo: (index: number) => void;
  setPlaying: (playing: boolean) => void;
  stop: () => void;
}

export const useBriefStore = create<BriefState>((set, get) => ({
  brief: null,
  index: 0,
  playing: false,
  start: (brief) => set({ brief, index: 0, playing: true }),
  goTo: (index) => {
    const { brief } = get();
    if (!brief) return;
    set({ index: Math.min(Math.max(index, 0), brief.scenes.length - 1) });
  },
  setPlaying: (playing) => set({ playing }),
  stop: () => set({ brief: null, index: 0, playing: false }),
}));
