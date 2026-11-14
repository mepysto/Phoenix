"use client";

import { useEffect, useState } from "react";
import { EVENT_TYPES } from "@phoenix/shared/constants";
import type { EventType } from "@phoenix/shared/types";
import { EventTypeIcon } from "@/components/event/EventTypeIcon";
import { eventsAPI, type EventFacets } from "@/lib/api/client";
import { useTranslation } from "@/lib/i18n/useTranslation";
import { SEVERITY_LEVELS, severityColor } from "@/lib/severity";
import { ALL_EVENT_TYPES, ALL_SEVERITIES, useEventStore } from "@/store/eventStore";

const ROW = "flex cursor-pointer items-center gap-3 rounded-lg px-2 py-1.5 hover:bg-gray-800/60";
const CHECKBOX = "h-4 w-4 rounded border-gray-600 bg-gray-700 text-primary-500 focus:ring-primary-500";

/** Counts behind each checkbox, under the other filters (same rules as the list) */
function useMapFacets(): EventFacets | null {
  const visibleTypes = useEventStore((s) => s.visibleTypes);
  const visibleSeverities = useEventStore((s) => s.visibleSeverities);
  const filter = useEventStore((s) => s.filter);
  const eventCount = useEventStore((s) => s.events.length);
  const [facets, setFacets] = useState<EventFacets | null>(null);

  useEffect(() => {
    let cancelled = false;
    eventsAPI
      .facets({
        q: filter.q,
        startDate: filter.startDate,
        types: visibleTypes.size && visibleTypes.size < ALL_EVENT_TYPES.length ? [...visibleTypes] : undefined,
        severities:
          visibleSeverities.size && visibleSeverities.size < ALL_SEVERITIES.length ? [...visibleSeverities] : undefined,
      })
      .then((f) => !cancelled && setFacets(f))
      .catch(() => {
        // Counts are a guide; the filters work without them
      });
    return () => {
      cancelled = true;
    };
  }, [visibleTypes, visibleSeverities, filter.q, filter.startDate, eventCount]);

  return facets;
}

function Count({ n }: { n: number | undefined }) {
  return <span className="ms-auto text-sm tabular-nums text-gray-400">{n ?? 0}</span>;
}

/**
 * Severity and type filters for the map (UX plan 5.1): each with how many
 * events it holds; types without any fold away.
 */
export function DisasterFilters() {
  const { t } = useTranslation();
  const visibleTypes = useEventStore((s) => s.visibleTypes);
  const visibleSeverities = useEventStore((s) => s.visibleSeverities);
  const toggleEventType = useEventStore((s) => s.toggleEventType);
  const toggleSeverity = useEventStore((s) => s.toggleSeverity);
  const facets = useMapFacets();
  const [showAllTypes, setShowAllTypes] = useState(false);

  const typeCount = (type: EventType) => facets?.byType[type] ?? 0;
  const withEvents = EVENT_TYPES.filter((type) => typeCount(type) > 0).sort((a, b) => typeCount(b) - typeCount(a));
  const empty = EVENT_TYPES.filter((type) => !withEvents.includes(type));
  // Until counts arrive, show every type rather than an empty list
  const shown = !facets || showAllTypes ? [...withEvents, ...empty] : withEvents;

  const setAllTypes = (on: boolean) => {
    const store = useEventStore.getState();
    store.setVisibility(on ? undefined : [], [...store.visibleSeverities]);
    void store.fetchEvents();
  };

  return (
    <div className="space-y-5">
      <section aria-labelledby="filter-severity">
        <h3 id="filter-severity" className="mb-1.5 px-2 text-sm font-semibold text-gray-200">
          {t.sidebar.severity}
        </h3>
        {[...SEVERITY_LEVELS].reverse().map((severity) => (
          <label key={severity} className={ROW}>
            <input
              type="checkbox"
              checked={visibleSeverities.has(severity)}
              onChange={() => toggleSeverity(severity)}
              className={CHECKBOX}
            />
            <span aria-hidden="true" className="h-3 w-3 rounded-full" style={{ backgroundColor: severityColor(severity) }} />
            <span className="text-sm text-gray-200">{t.sidebar[severity]}</span>
            <Count n={facets?.bySeverity[severity]} />
          </label>
        ))}
      </section>

      <section aria-labelledby="filter-types">
        <div className="mb-1.5 flex items-center justify-between gap-2 px-2">
          <h3 id="filter-types" className="text-sm font-semibold text-gray-200">
            {t.sidebar.eventTypes}
          </h3>
          <div className="flex gap-2 text-xs font-medium">
            <button type="button" onClick={() => setAllTypes(true)} className="text-primary-300 hover:underline">
              {t.ux.selectAll}
            </button>
            <button type="button" onClick={() => setAllTypes(false)} className="text-primary-300 hover:underline">
              {t.ux.selectNone}
            </button>
          </div>
        </div>
        {shown.map((type) => (
          <label key={type} className={ROW}>
            <input
              type="checkbox"
              checked={visibleTypes.has(type)}
              onChange={() => toggleEventType(type)}
              className={CHECKBOX}
            />
            <EventTypeIcon type={type} className="h-4 w-4 text-gray-300" />
            <span className="text-sm text-gray-200">{t.sidebar[type]}</span>
            <Count n={typeCount(type)} />
          </label>
        ))}
        {facets && empty.length > 0 && (
          <button
            type="button"
            aria-expanded={showAllTypes}
            onClick={() => setShowAllTypes((s) => !s)}
            className="mt-1 px-2 py-1 text-sm font-medium text-primary-300 hover:underline"
          >
            {showAllTypes ? t.events.fewerTypes : t.events.moreTypes.replace("{n}", String(empty.length))}
          </button>
        )}
      </section>
    </div>
  );
}
