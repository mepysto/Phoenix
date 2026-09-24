"use client";

import { useEffect } from "react";
import { VIEW_MODES } from "@/lib/map/viewModes";
import { useBriefStore } from "@/store/briefStore";
import { useMapStore } from "@/store/mapStore";
import { useRouteStore } from "@/store/routeStore";
import { useUiStore } from "@/store/uiStore";

/** Key → action, shown in the shortcuts help (keys are case-insensitive) */
export const SHORTCUTS = ["o", "l", "1", "2", "v", "/", "Escape", "?"] as const;
export type ShortcutKey = (typeof SHORTCUTS)[number];

function typing(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  return target.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName);
}

/** Map-page keyboard shortcuts (G-9) */
export function useKeyboardShortcuts(): void {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.ctrlKey || e.metaKey || e.altKey || typing(e.target)) return;
      const ui = useUiStore.getState();
      const map = useMapStore.getState();
      switch (e.key.length === 1 ? e.key.toLowerCase() : e.key) {
        case "o":
          ui.toggleOpsMode();
          break;
        case "l":
          ui.toggleSidebar();
          break;
        case "1":
          map.setBasemap("dark");
          break;
        case "2":
          map.setBasemap("satellite");
          break;
        case "v": {
          const next = VIEW_MODES[(VIEW_MODES.indexOf(map.viewMode) + 1) % VIEW_MODES.length]!;
          map.setViewMode(next);
          break;
        }
        case "/": {
          const search = document.getElementById("global-search");
          if (!search) return;
          search.focus();
          break;
        }
        case "?":
          ui.setShortcutsOpen(!ui.shortcutsOpen);
          break;
        case "Escape":
          // Close the topmost thing; a playing brief handles Escape itself
          if (useBriefStore.getState().brief) return;
          if (ui.shortcutsOpen) ui.setShortcutsOpen(false);
          else if (map.inspected) {
            map.setInspected(null);
            ui.setFollow(null);
          } else if (useRouteStore.getState().end) useRouteStore.getState().clear();
          else return;
          break;
        default:
          return;
      }
      e.preventDefault();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);
}
