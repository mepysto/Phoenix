"use client";

import dynamic from "next/dynamic";
import { useEffect } from "react";
import { useEventStore } from "@/store/eventStore";

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
  const { events, isLoading, error, fetchEvents, selectEvent } =
    useEventStore();

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
      <MapEngineWrapper
        events={events.length > 0 ? events : undefined}
        onEventClick={selectEvent}
      />
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
