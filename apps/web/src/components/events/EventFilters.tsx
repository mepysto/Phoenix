"use client";

import { useEffect, useState } from "react";
import { Search, X } from "lucide-react";
import { EVENT_TYPES } from "@phoenix/shared/constants";
import type { EventFacets, EventSort, EventType, SeverityLevel } from "@/lib/api/client";
import { EventTypeIcon } from "@/components/event/EventTypeIcon";
import { PERIODS, type EventQuery, type Period } from "@/lib/eventQuery";
import { useTranslation } from "@/lib/i18n/useTranslation";
import { severityColor } from "@/lib/severity";

const SEVERITIES_HIGH_FIRST: SeverityLevel[] = ["critical", "high", "medium", "low"];

const chip = (on: boolean) =>
  `flex shrink-0 items-center gap-1.5 rounded-full border px-3 py-1.5 text-sm font-medium transition-colors ${
    on
      ? "border-primary-400 bg-primary-400/15 text-white"
      : "border-gray-700 text-gray-300 hover:border-gray-500 hover:text-white"
  }`;

/** Add or remove a value; an empty selection means "all" (undefined) */
function toggle<T>(list: T[] | undefined, value: T): T[] | undefined {
  const next = list?.includes(value) ? list.filter((v) => v !== value) : [...(list ?? []), value];
  return next.length ? next : undefined;
}

function Count({ n }: { n: number | undefined }) {
  return <span className="tabular-nums text-gray-400">{n ?? 0}</span>;
}

/**
 * Filters for the disaster list (UX plan 5.2). Each chip shows how many
 * events choosing it gives; types without events fold away.
 */
export function EventFilters({
  query,
  facets,
  onChange,
}: {
  query: EventQuery;
  facets: EventFacets | null;
  onChange: (patch: Partial<EventQuery>) => void;
}) {
  const { t } = useTranslation();
  const e = t.events;
  const [draft, setDraft] = useState(query.q ?? "");
  const [showAllTypes, setShowAllTypes] = useState(false);
  useEffect(() => setDraft(query.q ?? ""), [query.q]);

  const typeCount = (type: EventType) => facets?.byType[type] ?? 0;
  const withEvents = EVENT_TYPES.filter((type) => typeCount(type) > 0 || query.types?.includes(type)).sort(
    (a, b) => typeCount(b) - typeCount(a),
  );
  const empty = EVENT_TYPES.filter((type) => !withEvents.includes(type));
  const shownTypes = showAllTypes ? [...withEvents, ...empty] : withEvents;
  const filtered = !!(query.types || query.severities || query.q || query.period);
  const periodLabel: Record<Period, string> = { "1": e.period1, "7": e.period7, "30": e.period30 };

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-3">
        <form
          role="search"
          className="relative min-w-0 flex-1 basis-64"
          onSubmit={(ev) => {
            ev.preventDefault();
            onChange({ q: draft.trim() || undefined });
          }}
        >
          <Search className="pointer-events-none absolute start-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" aria-hidden="true" />
          <label htmlFor="events-search" className="sr-only">
            {e.searchLabel}
          </label>
          <input
            id="events-search"
            type="search"
            value={draft}
            onChange={(ev) => setDraft(ev.target.value)}
            placeholder={t.common.searchPlaceholder}
            className="field !ps-9"
          />
        </form>
        <label className="flex items-center gap-2 text-sm text-gray-300">
          {e.period}
          <select
            value={query.period ?? ""}
            onChange={(ev) => onChange({ period: (ev.target.value || undefined) as Period | undefined })}
            className="field w-auto py-1.5"
          >
            <option value="">{e.periodAll}</option>
            {PERIODS.map((p) => (
              <option key={p} value={p}>
                {periodLabel[p]}
              </option>
            ))}
          </select>
        </label>
        <label className="flex items-center gap-2 text-sm text-gray-300">
          {e.sort}
          <select
            value={query.sort}
            onChange={(ev) => onChange({ sort: ev.target.value as EventSort })}
            className="field w-auto py-1.5"
          >
            <option value="importance">{e.sortImportance}</option>
            <option value="recent">{e.sortRecent}</option>
            <option value="affected">{e.sortAffected}</option>
          </select>
        </label>
      </div>

      <div role="group" aria-label={t.sidebar.severity} className="flex flex-wrap items-center gap-2">
        {SEVERITIES_HIGH_FIRST.map((severity) => {
          const on = !!query.severities?.includes(severity);
          return (
            <button
              key={severity}
              type="button"
              aria-pressed={on}
              onClick={() => onChange({ severities: toggle(query.severities, severity) })}
              className={chip(on)}
            >
              <span aria-hidden="true" className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: severityColor(severity) }} />
              {t.sidebar[severity]}
              <Count n={facets?.bySeverity[severity]} />
            </button>
          );
        })}
      </div>

      <div role="group" aria-label={t.sidebar.eventTypes} className="flex flex-wrap items-center gap-2">
        {shownTypes.map((type) => {
          const on = !!query.types?.includes(type);
          return (
            <button
              key={type}
              type="button"
              aria-pressed={on}
              onClick={() => onChange({ types: toggle(query.types, type) })}
              className={chip(on)}
            >
              <EventTypeIcon type={type} className="h-4 w-4 text-gray-300" />
              {t.sidebar[type] ?? type}
              <Count n={typeCount(type)} />
            </button>
          );
        })}
        {empty.length > 0 && (
          <button
            type="button"
            aria-expanded={showAllTypes}
            onClick={() => setShowAllTypes((s) => !s)}
            className="px-2 py-1.5 text-sm font-medium text-primary-300 hover:underline"
          >
            {showAllTypes ? e.fewerTypes : e.moreTypes.replace("{n}", String(empty.length))}
          </button>
        )}
        {filtered && (
          <button
            type="button"
            onClick={() =>
              onChange({ types: undefined, severities: undefined, q: undefined, period: undefined })
            }
            className="flex items-center gap-1 px-2 py-1.5 text-sm font-medium text-primary-300 hover:underline"
          >
            <X className="h-4 w-4" aria-hidden="true" />
            {e.clearFilters}
          </button>
        )}
      </div>
    </div>
  );
}
