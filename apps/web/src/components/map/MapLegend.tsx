"use client";

import { useMemo } from "react";
import { EVENT_TYPE_COLORS, EVENT_TYPE_LABELS, EVENT_TYPES } from "@phoenix/shared/constants";
import type { ApiDisasterEvent, EventType, SeverityLevel } from "@/lib/api/client";
import { useTranslation } from "@/lib/i18n/useTranslation";
import { getMarkerSize } from "@/lib/map/eventLayers";

/** Marker legend: colour = event type (only types on the map), size = severity */
export function MapLegend({ events }: { events: ApiDisasterEvent[] }) {
  const { t } = useTranslation();
  // Only list types actually on the map, in the canonical order
  const legendTypes = useMemo(() => {
    const present = new Set(events.map((e) => e.type as EventType));
    return EVENT_TYPES.filter((type) => present.has(type));
  }, [events]);

  return (
    <div className="absolute bottom-4 left-4 rounded-lg bg-gray-900/90 p-3 text-xs text-gray-300 shadow-lg backdrop-blur">
      <div className="mb-2 font-medium text-white">
        {t.map.activeEvents}: {events.length}
      </div>
      {/* Markers: colour = event type, size = severity (see eventsToGeoJSON) */}
      <div className="mb-2 flex max-w-xs flex-wrap gap-x-3 gap-y-1">
        {legendTypes.map((type) => (
          <div key={type} className="flex items-center gap-1">
            <span
              className="h-2 w-2 rounded-full"
              style={{ backgroundColor: EVENT_TYPE_COLORS[type] }}
            />
            <span>{EVENT_TYPE_LABELS[type]}</span>
          </div>
        ))}
      </div>
      <div className="flex items-center gap-3">
        {(["low", "medium", "high", "critical"] as SeverityLevel[]).map(
          (severity) => (
            <div key={severity} className="flex items-center gap-1">
              <span
                className="rounded-full bg-gray-400"
                style={{
                  width: getMarkerSize(severity),
                  height: getMarkerSize(severity),
                }}
              />
              <span className="capitalize">{severity}</span>
            </div>
          ),
        )}
      </div>
    </div>
  );
}
