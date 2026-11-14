import { create } from "zustand";
import type { ApiDisasterEvent } from "@/lib/api/client";

/** What the camera follows: a feature of an overlay identified by one property */
export interface FollowTarget {
  layerId: string;
  key: string;
  value: string | number;
}

/**
 * The map's right-hand panel shows one thing at a time (UX plan 5.1): the
 * selected event's summary, the list of events in view, or the assistant.
 * The event summary is driven by the map's selection; opening either of the
 * others clears it (GlobeViewer), and selecting an event closes them.
 */
export type RightPanel = "in-view" | "assistant" | null;

/** On phones the timeline and legend are opened from the View menu, one at a time (UX plan 5.1) */
export type PhoneOverlay = "timeline" | "legend" | null;

interface UiState {
  sidebarHidden: boolean;
  rightPanel: RightPanel;
  setRightPanel: (panel: RightPanel) => void;
  phoneOverlay: PhoneOverlay;
  togglePhoneOverlay: (overlay: Exclude<PhoneOverlay, null>) => void;
  /** An event to fly to and open; a fresh object each time so repeats fly again */
  focusEvent: ApiDisasterEvent | null;
  setFocusEvent: (event: ApiDisasterEvent | null) => void;
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
  rightPanel: null,
  setRightPanel: (rightPanel) => set({ rightPanel }),
  phoneOverlay: null,
  togglePhoneOverlay: (overlay) => set((s) => ({ phoneOverlay: s.phoneOverlay === overlay ? null : overlay })),
  focusEvent: null,
  setFocusEvent: (event) => set({ focusEvent: event ? { ...event } : null }),
  opsMode: false,
  shortcutsOpen: false,
  follow: null,
  toggleSidebar: () => set((s) => ({ sidebarHidden: !s.sidebarHidden })),
  toggleOpsMode: () => set((s) => ({ opsMode: !s.opsMode })),
  setShortcutsOpen: (shortcutsOpen) => set({ shortcutsOpen }),
  setFollow: (follow) => set({ follow }),
}));
