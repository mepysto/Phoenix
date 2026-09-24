import { create } from "zustand";
import type { ApiRoute } from "@/lib/api/client";

export type RouteMode = "auto" | "truck" | "pedestrian" | "bicycle";

export interface RoutePoint {
  lat: number;
  lng: number;
  label?: string;
}

interface RouteState {
  start: RoutePoint | null;
  end: RoutePoint | null;
  mode: RouteMode;
  /** Waiting for a map click to choose the start */
  pickingStart: boolean;
  result: ApiRoute | null;
  loading: boolean;
  error: string | null;
  /** Begin planning to a destination (the start is picked on the map) */
  routeTo: (end: RoutePoint) => void;
  setStart: (start: RoutePoint) => void;
  setMode: (mode: RouteMode) => void;
  setResult: (result: ApiRoute | null, error?: string | null) => void;
  setLoading: (loading: boolean) => void;
  clear: () => void;
}

export const useRouteStore = create<RouteState>((set) => ({
  start: null,
  end: null,
  mode: "auto",
  pickingStart: false,
  result: null,
  loading: false,
  error: null,
  routeTo: (end) => set({ end, start: null, pickingStart: true, result: null, error: null }),
  setStart: (start) => set({ start, pickingStart: false }),
  setMode: (mode) => set({ mode }),
  setResult: (result, error = null) => set({ result, error, loading: false }),
  setLoading: (loading) => set({ loading }),
  clear: () => set({ start: null, end: null, pickingStart: false, result: null, loading: false, error: null }),
}));
