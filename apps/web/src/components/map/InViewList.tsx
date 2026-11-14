"use client";

import { useMemo } from "react";
import { X } from "lucide-react";
import { EventTypeIcon } from "@/components/event/EventTypeIcon";
import type { ApiDisasterEvent } from "@/lib/api/client";
import { placeName } from "@/lib/eventPlace";
import { formatWhen } from "@/lib/format";
import { useTranslation } from "@/lib/i18n/useTranslation";
import { eventsInView } from "@/lib/map/inView";
import { severityColor } from "@/lib/severity";
import { useEventStore } from "@/store/eventStore";
import { useMapStore } from "@/store/mapStore";
import { useUiStore } from "@/store/uiStore";

/** The events behind the "in view" figure, most severe first; picking one flies there */
export function InViewList({ onSelect }: { onSelect: (event: ApiDisasterEvent) => void }) {
  const { t, lang } = useTranslation();
  const events = useEventStore((s) => s.events);
  const viewport = useMapStore((s) => s.viewport);
  const close = () => useUiStore.getState().setRightPanel(null);
  const list = useMemo(() => (viewport ? eventsInView(events, viewport.bbox) : []), [events, viewport]);

  return (
    <section
      aria-label={t.ux.inViewTitle}
      className="hud-panel pointer-events-auto absolute right-14 top-4 z-30 flex max-h-[calc(100%-2rem)] w-80 animate-panel-in flex-col rounded-xl"
    >
      <div className="flex items-center justify-between gap-2 border-b border-gray-700/80 px-4 py-3">
        <h2 className="text-sm font-semibold text-white">
          {t.ux.inViewTitle}
          <span className="ms-2 font-normal tabular-nums text-gray-400">{list.length.toLocaleString(lang)}</span>
        </h2>
        <button
          type="button"
          onClick={close}
          className="rounded-md p-1 text-gray-400 hover:bg-gray-800 hover:text-white"
          aria-label={t.common.close}
        >
          <X className="h-4 w-4" aria-hidden="true" />
        </button>
      </div>
      {list.length === 0 ? (
        <p className="px-4 py-3 text-sm text-gray-400">{t.events.noEvents}</p>
      ) : (
        <ul className="overflow-y-auto py-1">
          {list.map((event) => (
            <li key={event.id}>
              <button
                type="button"
                onClick={() => onSelect(event)}
                className="flex w-full items-start gap-3 px-4 py-2 text-start hover:bg-gray-800"
              >
                <span
                  aria-hidden="true"
                  className="mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full"
                  style={{ backgroundColor: severityColor(event.severity) }}
                />
                <span className="min-w-0 flex-1">
                  <span className="block text-sm font-medium text-gray-100">{event.title}</span>
                  <span className="mt-0.5 flex items-center gap-1.5 text-xs text-gray-400">
                    <EventTypeIcon type={event.type} className="h-3.5 w-3.5" />
                    <span className="truncate">{placeName(event)}</span>
                    <span aria-hidden="true">·</span>
                    <span className="shrink-0">{formatWhen(event.startDate, lang)}</span>
                  </span>
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
