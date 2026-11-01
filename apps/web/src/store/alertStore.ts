import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { WatchArea } from "@/lib/alerts";

export interface RecentAlert {
  key: string;
  eventId: string;
  title: string;
  areaName: string;
  distanceKm: number;
  at: string;
}

interface AlertState {
  areas: WatchArea[];
  /** "areaId:eventId" keys already alerted */
  seen: string[];
  recent: RecentAlert[];
  addArea: (area: WatchArea) => void;
  removeArea: (id: string) => void;
  record: (alerts: RecentAlert[]) => void;
}

const MAX_SEEN = 2000;
const MAX_RECENT = 30;

/** Watch areas live in this browser only (localStorage). */
export const useAlertStore = create<AlertState>()(
  persist(
    (set) => ({
      areas: [],
      seen: [],
      recent: [],
      addArea: (area) => set((s) => ({ areas: [...s.areas, area] })),
      removeArea: (id) =>
        set((s) => ({
          areas: s.areas.filter((a) => a.id !== id),
          recent: s.recent.filter((r) => !r.key.startsWith(`${id}:`)),
        })),
      record: (alerts) =>
        set((s) => ({
          seen: [...s.seen, ...alerts.map((a) => a.key)].slice(-MAX_SEEN),
          recent: [...alerts, ...s.recent].slice(0, MAX_RECENT),
        })),
    }),
    { name: "phoenix-alerts", version: 1 },
  ),
);
