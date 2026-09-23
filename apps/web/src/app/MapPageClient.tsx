"use client";

import dynamic from "next/dynamic";
import { useEffect } from "react";
import { useEventStore } from "@/store/eventStore";
import { DEMO_EVENTS, DEMO_MODE } from "@/lib/demo/demoEvents";
import { useTranslation } from "@/lib/i18n/useTranslation";

const MapEngineWrapper = dynamic(
  () => import("@/components/map/MapEngineWrapper"),
  {
    ssr: false,
    loading: () => (
      <div className="flex h-full w-full items-center justify-center bg-gray-900">
        <div className="text-center">
          <div className="mb-4 h-12 w-12 animate-spin rounded-full border-4 border-primary-500 border-t-transparent mx-auto" />
          <p className="text-gray-400">Loading Map Viewer...</p>
        </div>
      </div>
    ),
  },
);

export function MapPageClient() {
  const events = useEventStore((s) => s.events);
  const isLoading = useEventStore((s) => s.isLoading);
  const error = useEventStore((s) => s.error);
  const fetchEvents = useEventStore((s) => s.fetchEvents);
  const selectEvent = useEventStore((s) => s.selectEvent);
  const { t } = useTranslation();

  // Demo data is opt-in only; an empty result or API error must stay visibly empty
  const useDemo = DEMO_MODE && events.length === 0 && !isLoading;
  const displayedEvents = useDemo ? DEMO_EVENTS : events;
  const showEmptyState = !useDemo && !isLoading && !error && events.length === 0;

  useEffect(() => {
    fetchEvents();
  }, [fetchEvents]);

  return (
    <main className="relative flex-1">
      {error && (
        <div className="absolute left-1/2 top-4 z-50 -translate-x-1/2 rounded-lg bg-red-900/90 px-4 py-2 text-sm text-white">
          Failed to load events: {error}
        </div>
      )}
      {useDemo && (
        <div className="absolute left-1/2 top-4 z-50 -translate-x-1/2 rounded-lg bg-amber-700/90 px-4 py-2 text-sm text-white">
          Demo mode — sample data, not real events
        </div>
      )}
      <MapEngineWrapper events={displayedEvents} onEventClick={selectEvent} />
      {showEmptyState && (
        <div
          role="status"
          className="pointer-events-none absolute left-1/2 top-4 z-40 -translate-x-1/2 rounded-lg bg-gray-800/90 px-4 py-2 text-sm text-gray-200"
        >
          {t.events.noEvents} · {t.events.adjustFilters}
        </div>
      )}
      {isLoading && events.length === 0 && (
        <div className="absolute inset-0 flex items-center justify-center bg-gray-900/50">
          <div className="text-center">
            <div className="mb-4 h-8 w-8 animate-spin rounded-full border-4 border-primary-500 border-t-transparent mx-auto" />
            <p className="text-gray-300">Loading events...</p>
          </div>
        </div>
      )}
    </main>
  );
}
