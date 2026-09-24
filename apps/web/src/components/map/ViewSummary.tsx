"use client";

import { useEffect, useMemo, useState } from "react";
import { ChevronDown, MapPin } from "lucide-react";
import { EVENT_TYPE_COLORS } from "@phoenix/shared/constants";
import type { EventType } from "@phoenix/shared/types";
import { formatAge } from "@/components/layout/SourceStatusPanel";
import { viewAPI, type ApiDisasterEvent, type ApiNearby, type ApiViewSummary } from "@/lib/api/client";
import { useTranslation } from "@/lib/i18n/useTranslation";
import { nearbyRadiusKm } from "@/lib/viewSummary";
import { ALL_EVENT_TYPES, ALL_SEVERITIES, useEventStore } from "@/store/eventStore";
import { useMapStore } from "@/store/mapStore";

const FETCH_DEBOUNCE_MS = 300;

interface ViewSummaryProps {
  onSelect: (event: ApiDisasterEvent) => void;
}

/**
 * "What is on screen": totals for the visible area under the current
 * filters and instant, plus the events nearest to the map centre.
 */
export function ViewSummary({ onSelect }: ViewSummaryProps) {
  const { t, lang } = useTranslation();
  const viewport = useMapStore((s) => s.viewport);
  // The viewport comes from the 2D map; in the 3D engine it would be stale
  const engine = useMapStore((s) => s.engine);
  const visibleTypes = useEventStore((s) => s.visibleTypes);
  const visibleSeverities = useEventStore((s) => s.visibleSeverities);
  const at = useEventStore((s) => s.filter.at);
  // Live changes arrive through the event list; its size is a cheap refresh trigger
  const eventCount = useEventStore((s) => s.events.length);
  const [summary, setSummary] = useState<ApiViewSummary | null>(null);
  const [nearby, setNearby] = useState<ApiNearby | null>(null);
  const [nearbyOpen, setNearbyOpen] = useState(false);

  const filter = useMemo(
    () => ({
      types: visibleTypes.size < ALL_EVENT_TYPES.length ? [...visibleTypes] : undefined,
      severities:
        visibleSeverities.size < ALL_SEVERITIES.length ? [...visibleSeverities] : undefined,
      at,
    }),
    [visibleTypes, visibleSeverities, at],
  );

  useEffect(() => {
    if (!viewport) return;
    const controller = new AbortController();
    const timer = setTimeout(() => {
      viewAPI
        .summary(viewport.bbox, filter, controller.signal)
        .then(setSummary)
        .catch(() => {
          // Keep the last summary; the map itself still works
        });
    }, FETCH_DEBOUNCE_MS);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [viewport, filter, eventCount]);

  useEffect(() => {
    if (!viewport || !nearbyOpen) return;
    const controller = new AbortController();
    const { lat, lng } = viewport.center;
    const timer = setTimeout(() => {
      viewAPI
        .nearby(lat, lng, nearbyRadiusKm(viewport.zoom), filter, controller.signal)
        .then(setNearby)
        .catch(() => {
          // Keep the last list
        });
    }, FETCH_DEBOUNCE_MS);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [viewport, filter, nearbyOpen, eventCount]);

  if (!summary || engine === "cesium") return null;
  const critical = summary.bySeverity.critical ?? 0;
  const high = summary.bySeverity.high ?? 0;
  const updated = formatAge(summary.lastUpdated, lang);
  const number = new Intl.NumberFormat(lang);

  return (
    <section
      aria-label={t.view.label}
      className="pointer-events-auto w-60 rounded-lg bg-gray-900/90 text-xs text-gray-300 shadow-lg backdrop-blur"
    >
      <div className="px-3 py-2" aria-live="polite">
        <div className="flex items-baseline justify-between">
          <span>{t.view.inView}</span>
          <span className="text-lg font-semibold tabular-nums text-white">
            {number.format(summary.total)}
          </span>
        </div>
        {(critical > 0 || high > 0) && (
          <div className="mt-1 flex gap-3">
            {critical > 0 && (
              <span className="text-purple-300">
                {t.sidebar.critical} {number.format(critical)}
              </span>
            )}
            {high > 0 && (
              <span className="text-red-300">
                {t.sidebar.high} {number.format(high)}
              </span>
            )}
          </div>
        )}
        {summary.affectedPopulation > 0 && (
          <div className="mt-1">
            {t.view.affected.replace("{n}", number.format(summary.affectedPopulation))}
          </div>
        )}
        {updated && (
          <div className="mt-1 text-gray-500">{t.view.updated.replace("{time}", updated)}</div>
        )}
      </div>

      <button
        type="button"
        onClick={() => setNearbyOpen((open) => !open)}
        aria-expanded={nearbyOpen}
        className="flex w-full items-center gap-1 border-t border-gray-700/60 px-3 py-1.5 hover:bg-gray-800"
      >
        <MapPin className="h-3 w-3" aria-hidden="true" />
        <span className="flex-1 text-left">{t.view.nearby}</span>
        <ChevronDown
          className={`h-3 w-3 transition-transform ${nearbyOpen ? "rotate-180" : ""}`}
          aria-hidden="true"
        />
      </button>

      {nearbyOpen && nearby && (
        <ul className="max-h-64 overflow-y-auto border-t border-gray-700/60 py-1">
          {nearby.data.length === 0 && <li className="px-3 py-1 text-gray-500">{t.view.noneNearby}</li>}
          {nearby.data.map(({ event, distanceKm }) => (
            <li key={event.id}>
              <button
                type="button"
                onClick={() => onSelect(event)}
                className="flex w-full items-center gap-2 px-3 py-1 text-left hover:bg-gray-800"
              >
                <span
                  aria-hidden="true"
                  className="h-2 w-2 shrink-0 rounded-full"
                  style={{ backgroundColor: EVENT_TYPE_COLORS[event.type as EventType] ?? "#808080" }}
                />
                <span className="flex-1 truncate">{event.title}</span>
                <span className="shrink-0 tabular-nums text-gray-500">
                  {number.format(Math.round(distanceKm))} km
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
