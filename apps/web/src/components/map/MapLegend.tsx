"use client";

import { useMemo } from "react";
import { EVENT_TYPES } from "@phoenix/shared/constants";
import type { ApiDisasterEvent, EventType } from "@/lib/api/client";
import { EVENT_TYPE_ICONS } from "@/lib/eventTypeIcons";
import { useTranslation } from "@/lib/i18n/useTranslation";
import { SEVERITY_LEVELS, severityColor } from "@/lib/severity";
import { useUiStore } from "@/store/uiStore";

/**
 * Marker legend, matching lib/map/eventLayers: colour = severity, icon =
 * event type (only types on the map). The headline counts active events, the
 * same figure as the intro and the dashboard; ended events still drawn on the
 * map are noted separately. Always shown on wider screens; phones open it from View.
 */
export function MapLegend({ events }: { events: ApiDisasterEvent[] }) {
  const { t, lang } = useTranslation();
  // Phones open the legend from the View menu; it is always shown on wider screens
  const open = useUiStore((s) => s.phoneOverlay === "legend");
  const activeCount = useMemo(() => events.filter((e) => e.isActive).length, [events]);
  const legendTypes = useMemo(() => {
    const present = new Set(events.map((e) => e.type as EventType));
    return EVENT_TYPES.filter((type) => present.has(type));
  }, [events]);
  const number = (n: number) => n.toLocaleString(lang);

  return (
    <div
      className={`hud-panel absolute bottom-16 left-2 right-2 z-20 rounded-xl text-xs text-gray-200 lg:bottom-4 lg:left-4 lg:right-auto lg:block lg:max-w-xs ${
        open ? "block" : "hidden"
      }`}
    >
      <p className="px-3 pb-0 pt-3 font-medium text-white">
        {t.map.activeEvents}: <span className="tabular-nums">{number(activeCount)}</span>
      </p>
      <div id="map-legend-body" className="space-y-2.5 px-3 pb-3 pt-1">
        {events.length > activeCount && (
          <p className="text-gray-400">{t.map.onMapTotal.replace("{n}", number(events.length))}</p>
        )}
        <div>
          <p className="mb-1 text-gray-400">{t.map.legendSeverity}</p>
          <ul className="flex flex-wrap items-center gap-x-3 gap-y-1">
            {SEVERITY_LEVELS.map((severity) => (
              <li key={severity} className="flex items-center gap-1.5">
                <span
                  aria-hidden="true"
                  className="h-3 w-3 rounded-full ring-1 ring-white/70"
                  style={{ backgroundColor: severityColor(severity) }}
                />
                {t.sidebar[severity]}
              </li>
            ))}
          </ul>
        </div>
        {legendTypes.length > 0 && (
          <div>
            <p className="mb-1 text-gray-400">{t.map.legendType}</p>
            <ul className="flex flex-wrap gap-x-3 gap-y-1">
              {legendTypes.map((type) => {
                const Icon = EVENT_TYPE_ICONS[type];
                return (
                  <li key={type} className="flex items-center gap-1.5">
                    <Icon className="h-3.5 w-3.5 text-gray-300" aria-hidden="true" />
                    {t.sidebar[type]}
                  </li>
                );
              })}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
