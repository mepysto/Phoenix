"use client";

import { useMemo, useState } from "react";
import { ChevronDown, ListFilter } from "lucide-react";
import { EVENT_TYPES } from "@phoenix/shared/constants";
import type { ApiDisasterEvent, EventType } from "@/lib/api/client";
import { EVENT_TYPE_ICONS } from "@/lib/eventTypeIcons";
import { useTranslation } from "@/lib/i18n/useTranslation";
import { SEVERITY_LEVELS, severityColor } from "@/lib/severity";

/**
 * Marker legend, matching lib/map/eventLayers: colour = severity, icon =
 * event type (only types on the map). The headline counts active events, the
 * same figure as the intro and the dashboard; ended events still drawn on the
 * map are noted separately. Always open on wider screens; a chip on phones.
 */
export function MapLegend({ events }: { events: ApiDisasterEvent[] }) {
  const { t, lang } = useTranslation();
  const [open, setOpen] = useState(false);
  const activeCount = useMemo(() => events.filter((e) => e.isActive).length, [events]);
  const legendTypes = useMemo(() => {
    const present = new Set(events.map((e) => e.type as EventType));
    return EVENT_TYPES.filter((type) => present.has(type));
  }, [events]);
  const number = (n: number) => n.toLocaleString(lang);

  return (
    <div className="hud-panel absolute bottom-4 left-4 z-20 max-w-[calc(100%-8rem)] rounded-xl text-xs text-gray-200 md:max-w-xs">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        aria-controls="map-legend-body"
        className="flex w-full items-center gap-2 px-3 py-2 text-start font-medium text-white md:pointer-events-none md:pb-0 md:pt-3"
      >
        <ListFilter className="h-3.5 w-3.5 text-gray-400 md:hidden" aria-hidden="true" />
        <span>
          {t.map.activeEvents}: <span className="tabular-nums">{number(activeCount)}</span>
        </span>
        <ChevronDown
          className={`h-3.5 w-3.5 text-gray-400 transition-transform md:hidden ${open ? "rotate-180" : ""}`}
          aria-hidden="true"
        />
      </button>
      <div id="map-legend-body" className={`${open ? "block" : "hidden"} space-y-2.5 px-3 pb-3 pt-1 md:block`}>
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
