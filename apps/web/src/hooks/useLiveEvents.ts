"use client";

import { useEffect, useState } from "react";
import { API_URL } from "@/lib/api/client";
import { EventStream, eventStreamUrl, type StreamStatus } from "@/lib/realtime/eventStream";
import { useEventStore } from "@/store/eventStore";
import { useSettingsStore } from "@/store/settingsStore";

/**
 * Keep the event store current while the map is open.
 *
 * Settings > Auto refresh turns live updates on/off. While the WebSocket is
 * not live (reconnecting, blocked by a proxy), the store is polled every
 * `refreshInterval` minutes so data never silently goes stale.
 */
export function useLiveEvents(): StreamStatus {
  const autoRefresh = useSettingsStore((s) => s.autoRefresh);
  const refreshInterval = useSettingsStore((s) => s.refreshInterval);
  const applyEventChanges = useEventStore((s) => s.applyEventChanges);
  const fetchEvents = useEventStore((s) => s.fetchEvents);
  const [status, setStatus] = useState<StreamStatus>("stopped");

  useEffect(() => {
    if (!autoRefresh) return;
    const stream = new EventStream({
      url: eventStreamUrl(API_URL),
      onChanges: (ids) => void applyEventChanges(ids),
      onResync: () => void fetchEvents(),
      onStatus: setStatus,
    });
    stream.start();
    return () => stream.stop();
  }, [autoRefresh, applyEventChanges, fetchEvents]);

  const live = status === "live";
  useEffect(() => {
    if (!autoRefresh || live) return;
    const timer = setInterval(() => void fetchEvents(), refreshInterval * 60_000);
    return () => clearInterval(timer);
  }, [autoRefresh, live, refreshInterval, fetchEvents]);

  return autoRefresh ? status : "stopped";
}
