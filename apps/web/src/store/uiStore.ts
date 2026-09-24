import { create } from "zustand";

/** What the camera follows: a feature of an overlay identified by one property */
export interface FollowTarget {
  layerId: string;
  key: string;
  value: string | number;
}

interface UiState {
  sidebarHidden: boolean;
  /** Operations console: full-screen map with a UTC clock (G-9/M7) */
  opsMode: boolean;
  shortcutsOpen: boolean;
  follow: FollowTarget | null;
  toggleSidebar: () => void;
  toggleOpsMode: () => void;
  setShortcutsOpen: (open: boolean) => void;
  setFollow: (target: FollowTarget | null) => void;
}

export const useUiStore = create<UiState>((set) => ({
  sidebarHidden: false,
  opsMode: false,
  shortcutsOpen: false,
  follow: null,
  toggleSidebar: () => set((s) => ({ sidebarHidden: !s.sidebarHidden })),
  toggleOpsMode: () => set((s) => ({ opsMode: !s.opsMode })),
  setShortcutsOpen: (shortcutsOpen) => set({ shortcutsOpen }),
  setFollow: (follow) => set({ follow }),
}));
