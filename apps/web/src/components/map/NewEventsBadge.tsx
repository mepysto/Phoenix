"use client";

import { useEffect, useMemo } from "react";
import { Bell, X } from "lucide-react";
import type { ApiDisasterEvent } from "@/lib/api/client";
import { useTranslation } from "@/lib/i18n/useTranslation";
import { useEventStore } from "@/store/eventStore";

/** How often expired marks are dropped */
const PRUNE_INTERVAL_MS = 30_000;

/**
 * "N new disasters" since the map was opened. Live updates otherwise merge
 * silently, so an operator could miss a new event; this names the count and
 * jumps to the newest one.
 */
export function NewEventsBadge({ onSelect }: { onSelect: (event: ApiDisasterEvent) => void }) {
  const { t } = useTranslation();
  const events = useEventStore((s) => s.events);
  const newEvents = useEventStore((s) => s.newEvents);
  const clearNewEvents = useEventStore((s) => s.clearNewEvents);
  const pruneNewEvents = useEventStore((s) => s.pruneNewEvents);

  const hasMarks = Object.keys(newEvents).length > 0;
  useEffect(() => {
    if (!hasMarks) return;
    const timer = setInterval(() => pruneNewEvents(), PRUNE_INTERVAL_MS);
    return () => clearInterval(timer);
  }, [hasMarks, pruneNewEvents]);

  // Only marks for events still on the map; newest arrival first
  const arrivals = useMemo(
    () =>
      events
        .filter((e) => e.id in newEvents)
        .sort((a, b) => newEvents[b.id]! - newEvents[a.id]!),
    [events, newEvents],
  );

  const newest = arrivals[0];
  return (
    <div aria-live="polite">
      {newest && (
        <div className="pointer-events-auto flex items-center rounded-full bg-red-700/95 text-xs font-medium text-white shadow-lg">
          <button
            type="button"
            onClick={() => onSelect(newest)}
            title={t.map.showNewest}
            className="flex items-center gap-1.5 rounded-l-full py-1 pl-3 pr-2 hover:bg-red-600"
          >
            <Bell className="h-3.5 w-3.5" aria-hidden="true" />
            {t.map.newEvents.replace("{n}", String(arrivals.length))}
          </button>
          <button
            type="button"
            onClick={clearNewEvents}
            aria-label={t.map.dismissNew}
            className="rounded-r-full py-1 pl-1 pr-2 hover:bg-red-600"
          >
            <X className="h-3.5 w-3.5" aria-hidden="true" />
          </button>
        </div>
      )}
    </div>
  );
}
