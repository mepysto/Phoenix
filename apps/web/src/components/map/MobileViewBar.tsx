"use client";

import { useMemo } from "react";
import { ChevronUp } from "lucide-react";
import { useTranslation } from "@/lib/i18n/useTranslation";
import { eventsInView } from "@/lib/map/inView";
import { useEventStore } from "@/store/eventStore";
import { useMapStore } from "@/store/mapStore";
import { useUiStore } from "@/store/uiStore";

/**
 * Phones (UX plan 5.1): one line at the bottom of the map, leaving the map
 * credits' (i) button clear, "86 in view ·
 * Critical 5", that opens the list of those events. The list and an event's
 * summary rise from the same place.
 */
export function MobileViewBar() {
  const { t, lang } = useTranslation();
  const events = useEventStore((s) => s.events);
  const viewport = useMapStore((s) => s.viewport);
  const engine = useMapStore((s) => s.engine);
  const rightPanel = useUiStore((s) => s.rightPanel);
  const inView = useMemo(() => (viewport ? eventsInView(events, viewport.bbox) : []), [events, viewport]);
  if (!viewport || engine === "cesium" || rightPanel === "in-view") return null;

  const critical = inView.filter((e) => e.severity === "critical").length;
  return (
    <button
      type="button"
      onClick={() => useUiStore.getState().setRightPanel("in-view")}
      aria-haspopup="dialog"
      className="hud-panel pointer-events-auto absolute bottom-2 left-2 right-12 z-30 flex items-center gap-2 rounded-xl px-4 py-3 text-sm text-gray-100 lg:hidden"
    >
      <span className="font-semibold">{t.ux.inViewCount.replace("{n}", inView.length.toLocaleString(lang))}</span>
      {critical > 0 && (
        <span className="text-purple-300">
          · {t.sidebar.critical} {critical.toLocaleString(lang)}
        </span>
      )}
      <ChevronUp className="ms-auto h-4 w-4 text-gray-400" aria-hidden="true" />
    </button>
  );
}
