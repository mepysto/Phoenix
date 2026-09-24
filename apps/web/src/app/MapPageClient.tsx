"use client";

import dynamic from "next/dynamic";
import { Suspense, useEffect, useState } from "react";
import { eventsAPI, type ApiDisasterEvent } from "@/lib/api/client";
import { useEventStore } from "@/store/eventStore";
import { DEMO_EVENTS, DEMO_MODE } from "@/lib/demo/demoEvents";
import { useTranslation } from "@/lib/i18n/useTranslation";
import { useLiveEvents } from "@/hooks/useLiveEvents";
import { useMapUrlState } from "@/hooks/useMapUrlState";
import { AgentPanel } from "@/components/agent/AgentPanel";
import { BriefPlayer } from "@/components/map/BriefPlayer";
import { FeatureInspector } from "@/components/map/FeatureInspector";
import { Timeline } from "@/components/map/Timeline";
import { ViewSummary } from "@/components/map/ViewSummary";

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

function MapPageContent() {
  const events = useEventStore((s) => s.events);
  const isLoading = useEventStore((s) => s.isLoading);
  const error = useEventStore((s) => s.error);
  const selectEvent = useEventStore((s) => s.selectEvent);
  const { t } = useTranslation();
  const liveStatus = useLiveEvents();

  // Demo data is opt-in only; an empty result or API error must stay visibly empty
  const useDemo = DEMO_MODE && events.length === 0 && !isLoading;
  const displayedEvents = useDemo ? DEMO_EVENTS : events;
  const showEmptyState = !useDemo && !isLoading && !error && events.length === 0;

  // URL state (camera, basemap, filters) is applied before the first fetch
  const { initial, onViewChange } = useMapUrlState();

  // "View on Globe" links to /?event=<id>: load it even if outside the current filter
  const focusId = initial.event;
  const [focusEvent, setFocusEvent] = useState<ApiDisasterEvent | null>(null);
  useEffect(() => {
    if (!focusId) return;
    let cancelled = false;
    eventsAPI
      .get(focusId)
      .then((event) => {
        if (!cancelled) setFocusEvent(event);
      })
      .catch(() => {
        // Unknown or deleted event: just show the map
      });
    return () => {
      cancelled = true;
    };
  }, [focusId]);

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
      <MapEngineWrapper
        events={displayedEvents}
        onEventClick={selectEvent}
        focusEvent={focusEvent}
        initialView={initial.view}
        initialProjection={initial.projection}
        onViewChange={onViewChange}
      />
      {liveStatus !== "stopped" && (
        <div
          role="status"
          className="pointer-events-none absolute left-4 top-[12.75rem] z-40 flex items-center gap-2 rounded-full bg-gray-900/90 px-3 py-1 text-xs text-gray-300"
        >
          <span
            aria-hidden="true"
            className={`h-2 w-2 rounded-full ${
              liveStatus === "live" ? "bg-green-500" : "animate-pulse bg-amber-500"
            }`}
          />
          {liveStatus === "live" ? t.map.live : t.map.reconnecting}
        </div>
      )}
      <div className="pointer-events-none absolute left-1/2 top-4 z-40 w-[min(32rem,calc(100%-2rem))] -translate-x-1/2">
        <BriefPlayer />
      </div>
      {/* Left column, above the legend */}
      <div className="pointer-events-none absolute bottom-44 left-4 z-30">
        <FeatureInspector />
      </div>
      {/* Bottom-right, above the scale bar and clear of the timeline */}
      <div className="pointer-events-none absolute bottom-16 right-4 z-40 flex flex-col items-end md:bottom-36">
        <AgentPanel onSelectEvent={(event) => setFocusEvent({ ...event })} />
      </div>
      <div className="pointer-events-none absolute left-4 top-[15.25rem] z-30">
        {/* A fresh object so picking the same event again flies there again */}
        <ViewSummary onSelect={(event) => setFocusEvent({ ...event })} />
      </div>
      {/* Between the legend (bottom-left, max ~22rem) and the scale bar (bottom-right); stacked above the legend on mobile */}
      <div className="pointer-events-none absolute bottom-40 left-4 right-4 z-30 md:bottom-9 md:left-[23rem] md:right-32">
        <Timeline />
      </div>
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

// useSearchParams() needs a Suspense boundary for static rendering
export function MapPageClient() {
  return (
    <Suspense>
      <MapPageContent />
    </Suspense>
  );
}
