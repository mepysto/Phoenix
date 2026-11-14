"use client";

import dynamic from "next/dynamic";
import { Suspense, useEffect, useState } from "react";
import { eventsAPI, type ApiDisasterEvent } from "@/lib/api/client";
import { useEventStore } from "@/store/eventStore";
import { DEMO_EVENTS, DEMO_MODE } from "@/lib/demo/demoEvents";
import { useTranslation } from "@/lib/i18n/useTranslation";
import { useLiveEvents } from "@/hooks/useLiveEvents";
import { useAreaAlerts } from "@/hooks/useAreaAlerts";
import { NewEventsBadge } from "@/components/map/NewEventsBadge";
import { useMapUrlState } from "@/hooks/useMapUrlState";
import { AgentPanel } from "@/components/agent/AgentPanel";
import { BriefPlayer } from "@/components/map/BriefPlayer";
import { FeatureInspector } from "@/components/map/FeatureInspector";
import { OpsClock } from "@/components/map/OpsClock";
import { ShortcutsHelp } from "@/components/map/ShortcutsHelp";
import { useFollowCamera } from "@/hooks/useFollowCamera";
import { useKeyboardShortcuts } from "@/hooks/useKeyboardShortcuts";
import { RoutePlanner } from "@/components/map/RoutePlanner";
import { Timeline } from "@/components/map/Timeline";
import { ViewSummary } from "@/components/map/ViewSummary";
import { IntroGlobe } from "@/components/brand/IntroGlobe";
import { MapFilterChips } from "@/components/map/MapFilterChips";
import { PhoenixMark } from "@/components/brand/PhoenixMark";

const MapEngineWrapper = dynamic(
  () => import("@/components/map/MapEngineWrapper"),
  {
    ssr: false,
    loading: () => (
      <div className="flex h-full w-full items-center justify-center bg-gray-950">
        <PhoenixMark className="h-10 w-10 animate-pulse text-gray-300" />
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
  useAreaAlerts();
  useKeyboardShortcuts();
  useFollowCamera();

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
        <div role="alert" className="absolute left-1/2 top-4 z-50 -translate-x-1/2 rounded-lg border border-ember-600/60 bg-gray-950/95 px-4 py-2 text-sm text-ember-300">
          Failed to load events: {error}
        </div>
      )}
      {useDemo && (
        <div className="absolute left-1/2 top-4 z-50 -translate-x-1/2 rounded-lg bg-amber-700/90 px-4 py-2 text-sm text-white">
          {t.map.demo}
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
      {/* Beside the map toolbar: live status, new events, what is in view */}
      <div className="pointer-events-none absolute left-[4.25rem] top-4 z-30 flex flex-col items-start gap-2">
        <div className="flex flex-wrap items-center gap-2">
        {liveStatus !== "stopped" && (
          <div
            role="status"
            className="hud-panel flex items-center gap-2 rounded-full px-3 py-1 text-xs font-medium text-gray-200"
          >
            <span aria-hidden="true" className="relative flex h-2 w-2">
              {liveStatus === "live" && (
                <span className="absolute inset-0 animate-ring-pulse rounded-full bg-primary-400" />
              )}
              <span
                className={`relative h-2 w-2 rounded-full ${
                  liveStatus === "live" ? "bg-primary-400" : "animate-pulse bg-amber-400"
                }`}
              />
            </span>
            {liveStatus === "live" ? t.map.live : t.map.reconnecting}
          </div>
        )}
        <NewEventsBadge
          onSelect={(event) => {
            selectEvent(event); // clears its new mark
            setFocusEvent({ ...event });
          }}
        />
        </div>
        <MapFilterChips />
        {/* A fresh object so picking the same event again flies there again */}
        <ViewSummary onSelect={(event) => setFocusEvent({ ...event })} />
      </div>
      <div className="pointer-events-none absolute left-1/2 top-4 z-40 w-[min(32rem,calc(100%-2rem))] -translate-x-1/2">
        <BriefPlayer />
      </div>
      <div className="pointer-events-none absolute bottom-[11rem] left-1/2 z-40 -translate-x-1/2 md:bottom-32">
        <OpsClock />
      </div>
      <ShortcutsHelp />
      {/* Left column, above the legend */}
      <div className="pointer-events-none absolute bottom-44 left-4 z-30 flex flex-col gap-2">
        <FeatureInspector />
        <RoutePlanner />
      </div>
      {/* Bottom corner beside the legend on phones; above the scale bar and timeline on wider screens */}
      <div className="pointer-events-none absolute bottom-4 right-4 z-40 flex flex-col items-end md:bottom-36">
        <AgentPanel onSelectEvent={(event) => setFocusEvent({ ...event })} />
      </div>
      {/* Between the legend (max ~22rem) and the scale bar; above the legend and assistant buttons on phones */}
      <div className="pointer-events-none absolute bottom-16 left-4 right-4 z-30 md:bottom-9 md:left-[23rem] md:right-32">
        <Timeline />
      </div>
      {showEmptyState && (
        <div
          role="status"
          className="hud-panel pointer-events-none absolute left-1/2 top-4 z-40 -translate-x-1/2 rounded-lg px-4 py-2 text-sm text-gray-200"
        >
          {t.events.noEvents} · {t.events.adjustFilters}
        </div>
      )}
      {isLoading && events.length === 0 && (
        <div className="pointer-events-none absolute inset-x-0 top-0 z-40 h-0.5 overflow-hidden" role="status" aria-label={t.common.loading}>
          <div className="h-full w-1/3 animate-[loading-bar_1.2s_ease-in-out_infinite] bg-primary-400" />
        </div>
      )}
      <IntroGlobe events={displayedEvents} />
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
