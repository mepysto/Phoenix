"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import {
  parseMapUrlState,
  serializeMapUrlState,
  type MapUrlState,
  type MapView,
} from "@/lib/map/urlState";
import { useEventStore } from "@/store/eventStore";
import { useMapStore } from "@/store/mapStore";
import { useSettingsStore } from "@/store/settingsStore";
import { useTimelineStore } from "@/store/timelineStore";

const WRITE_DEBOUNCE_MS = 400;

/**
 * Two-way sync between the map page and its URL (shareable deep links).
 *
 * On mount the URL wins over saved settings (basemap, visible filters) and is
 * applied before the first fetch. Afterwards camera, projection, basemap and
 * filter changes are written back with history.replaceState (debounced) so
 * panning does not flood the browser history.
 */
export function useMapUrlState(): {
  initial: MapUrlState;
  onViewChange: (view: MapView, projection: "globe" | "mercator") => void;
} {
  const searchParams = useSearchParams();
  const [initial] = useState(() => parseMapUrlState(new URLSearchParams(searchParams.toString())));
  const camera = useRef<Pick<MapUrlState, "view" | "projection">>({
    view: initial.view,
    projection: initial.projection,
  });
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const write = useCallback(() => {
    const { visibleTypes, visibleSeverities } = useEventStore.getState();
    const { basemap } = useMapStore.getState();
    const qs = serializeMapUrlState(
      {
        ...camera.current,
        basemap,
        types: [...visibleTypes],
        severities: [...visibleSeverities],
        event: initial.event,
        at: useTimelineStore.getState().at ?? undefined,
      },
      new URLSearchParams(window.location.search),
    );
    const url = `${window.location.pathname}${qs ? `?${qs}` : ""}`;
    if (url !== `${window.location.pathname}${window.location.search}`) {
      window.history.replaceState(window.history.state, "", url);
    }
  }, [initial.event]);

  const scheduleWrite = useCallback(() => {
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(write, WRITE_DEBOUNCE_MS);
  }, [write]);

  // Apply URL state once, before the first fetch
  useEffect(() => {
    const defaultBasemap = useSettingsStore.getState().defaultBasemap;
    useMapStore.getState().setBasemap(initial.basemap ?? defaultBasemap);
    const events = useEventStore.getState();
    events.setVisibility(initial.types, initial.severities);
    useTimelineStore.getState().setAt(initial.at ?? null);
    // Also clears a text search carried over from /events (and fetches)
    events.setFilter({ q: undefined, at: initial.at });
  }, [initial]);

  useEffect(() => {
    const unsubscribeEvents = useEventStore.subscribe((state, prev) => {
      if (
        state.visibleTypes !== prev.visibleTypes ||
        state.visibleSeverities !== prev.visibleSeverities
      ) {
        scheduleWrite();
      }
    });
    const unsubscribeMap = useMapStore.subscribe((state, prev) => {
      if (state.basemap !== prev.basemap) scheduleWrite();
    });
    const unsubscribeTimeline = useTimelineStore.subscribe((state, prev) => {
      if (state.at !== prev.at) scheduleWrite();
    });
    return () => {
      unsubscribeEvents();
      unsubscribeMap();
      unsubscribeTimeline();
      if (timer.current) clearTimeout(timer.current);
    };
  }, [scheduleWrite]);

  const onViewChange = useCallback(
    (view: MapView, projection: "globe" | "mercator") => {
      camera.current = { view, projection };
      scheduleWrite();
    },
    [scheduleWrite],
  );

  return { initial, onViewChange };
}
