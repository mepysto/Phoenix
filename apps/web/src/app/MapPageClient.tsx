"use client";

import dynamic from "next/dynamic";
import { Suspense, useEffect } from "react";
import { eventsAPI } from "@/lib/api/client";
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
import { InViewList } from "@/components/map/InViewList";
import { MobileViewBar } from "@/components/map/MobileViewBar";
import { LiveStatus } from "@/components/map/LiveStatus";
import { IntroGlobe } from "@/components/brand/IntroGlobe";
import { MapFilterChips } from "@/components/map/MapFilterChips";
import { useUiStore } from "@/store/uiStore";
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
  const focusEvent = useUiStore((s) => s.focusEvent);
  const setFocusEvent = useUiStore((s) => s.setFocusEvent);
  const rightPanel = useUiStore((s) => s.rightPanel);
  const phoneOverlay = useUiStore((s) => s.phoneOverlay);
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
  }, [focusId, setFocusEvent]);

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
      {/* Under the map toolbar: live status, new events, filters from the link, what is in view (phones) */}
      <div className="pointer-events-none absolute left-4 top-16 z-30 flex flex-col items-start gap-2">
        <div className="flex flex-wrap items-center gap-2">
        {liveStatus !== "stopped" && <LiveStatus status={liveStatus === "live" ? "live" : "reconnecting"} />}
        <NewEventsBadge
          onSelect={(event) => {
            selectEvent(event); // clears its new mark
            setFocusEvent({ ...event });
          }}
        />
        </div>
        <MapFilterChips />
      </div>
      {/* Phones: one line at the bottom; wider screens show the in-view card in the left panel */}
      <MobileViewBar />
      {rightPanel === "in-view" && <InViewList onSelect={setFocusEvent} />}
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
      <div className="pointer-events-none absolute bottom-16 right-4 z-40 flex flex-col items-end lg:bottom-36">
        <AgentPanel onSelectEvent={(event) => setFocusEvent({ ...event })} />
      </div>
      {/* Between the legend (max ~22rem) and the scale bar; above the legend and assistant buttons on phones */}
      {/* Phones open the timeline from the View menu */}
      <div
        className={`pointer-events-none absolute bottom-16 left-2 right-2 z-30 lg:bottom-9 lg:left-[23rem] lg:right-32 lg:block ${
          phoneOverlay === "timeline" ? "block" : "hidden"
        }`}
      >
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
