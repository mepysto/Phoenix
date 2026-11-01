import type { ItemKind } from "@/lib/sphere";

/** Kept apart from PlanMap so pages can use the colours without loading MapLibre */
export const KIND_COLORS: Record<ItemKind, string> = {
  tent: "#c9d3e2",
  tap: "#38bdf8",
  toilet: "#a78bfa",
  health: "#34d0ac",
  distribution: "#f5b83d",
};
