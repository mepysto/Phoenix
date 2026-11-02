"use client";

import { useMemo, useState } from "react";
import { ChevronDown, ListFilter } from "lucide-react";
import { EVENT_TYPE_COLORS, EVENT_TYPES } from "@phoenix/shared/constants";
import type { ApiDisasterEvent, EventType, SeverityLevel } from "@/lib/api/client";
import { useTranslation } from "@/lib/i18n/useTranslation";
import { getMarkerSize } from "@/lib/map/eventLayers";

/**
 * Marker legend: colour = event type (only types on the map), size = severity.
 * Always open on wider screens; a chip that expands on phones.
 */
export function MapLegend({ events }: { events: ApiDisasterEvent[] }) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  // Only list types actually on the map, in the canonical order
  const legendTypes = useMemo(() => {
    const present = new Set(events.map((e) => e.type as EventType));
    return EVENT_TYPES.filter((type) => present.has(type));
  }, [events]);

  return (
    <div className="hud-panel absolute bottom-4 left-4 z-20 max-w-[calc(100%-8rem)] rounded-xl text-xs text-gray-300 md:max-w-none">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        aria-controls="map-legend-body"
        className="flex w-full items-center gap-2 px-3 py-2 font-medium text-white md:pointer-events-none md:pb-0 md:pt-3"
      >
        <ListFilter className="h-3.5 w-3.5 text-gray-400 md:hidden" aria-hidden="true" />
        <span>
          {t.map.activeEvents}: <span className="tabular-nums">{events.length}</span>
        </span>
        <ChevronDown
          className={`h-3.5 w-3.5 text-gray-400 transition-transform md:hidden ${open ? "rotate-180" : ""}`}
          aria-hidden="true"
        />
      </button>
      <div
        id="map-legend-body"
        className={`${open ? "block" : "hidden"} px-3 pb-3 pt-2 md:block`}
      >
        {/* Markers: colour = event type, size = severity (see eventsToGeoJSON) */}
        <ul className="mb-2 flex max-w-xs flex-wrap gap-x-3 gap-y-1">
          {legendTypes.map((type) => (
            <li key={type} className="flex items-center gap-1.5">
              <span
                aria-hidden="true"
                className="h-2 w-2 rounded-full"
                style={{ backgroundColor: EVENT_TYPE_COLORS[type] }}
              />
              {t.sidebar[type]}
            </li>
          ))}
        </ul>
        <ul className="flex items-center gap-3">
          {(["low", "medium", "high", "critical"] as SeverityLevel[]).map(
            (severity) => (
              <li key={severity} className="flex items-center gap-1.5">
                <span
                  aria-hidden="true"
                  className="rounded-full bg-gray-400"
                  style={{
                    width: getMarkerSize(severity),
                    height: getMarkerSize(severity),
                  }}
                />
                {t.sidebar[severity]}
              </li>
            ),
          )}
        </ul>
      </div>
    </div>
  );
}
