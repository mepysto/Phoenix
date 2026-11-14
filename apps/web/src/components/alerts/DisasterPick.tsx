"use client";

import { useEffect, useState } from "react";
import { EventTypeIcon } from "@/components/event/EventTypeIcon";
import { eventsAPI, type ApiDisasterEvent } from "@/lib/api/client";
import { getEventPosition } from "@/lib/eventPosition";
import { placeName } from "@/lib/eventPlace";
import { useTranslation } from "@/lib/i18n/useTranslation";

/** Find an ongoing disaster by name and use its place as the alert centre */
export function DisasterPick({ onPick }: { onPick: (name: string, lat: number, lng: number) => void }) {
  const { t } = useTranslation();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<ApiDisasterEvent[]>([]);

  useEffect(() => {
    const q = query.trim();
    if (q.length < 2) {
      setResults([]);
      return;
    }
    let cancelled = false;
    const timer = setTimeout(() => {
      eventsAPI
        .list({ q, isActive: true }, 5, 0, "importance")
        .then((r) => !cancelled && setResults(r.data))
        .catch(() => !cancelled && setResults([]));
    }, 250);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [query]);

  return (
    <div>
      <label htmlFor="area-disaster" className="field-label">
        {t.ux.alertsFromDisaster}
      </label>
      <input
        id="area-disaster"
        type="search"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder={t.events.searchLabel}
        className="field"
        autoComplete="off"
      />
      {results.length > 0 && (
        <ul className="mt-1 overflow-hidden rounded-lg border border-gray-700">
          {results.map((event) => {
            const position = getEventPosition(event);
            if (!position) return null;
            return (
              <li key={event.id}>
                <button
                  type="button"
                  onClick={() => {
                    onPick(placeName(event), Number(position.lat.toFixed(2)), Number(position.lng.toFixed(2)));
                    setQuery("");
                  }}
                  className="flex w-full items-center gap-2 px-3 py-2 text-start text-sm text-gray-200 hover:bg-gray-800"
                >
                  <EventTypeIcon type={event.type} className="h-4 w-4 shrink-0 text-gray-400" />
                  <span className="min-w-0 flex-1 truncate">{event.title}</span>
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
