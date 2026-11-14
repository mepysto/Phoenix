"use client";

import { severityColor } from "@/lib/severity";
import { Suspense, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import {
  AlertTriangle,
  MapPin,
  Users,
  Clock,
  ChevronRight,
} from "lucide-react";
import {
  EVENT_TYPE_LABELS,
  EVENT_TYPE_COLORS,
} from "@phoenix/shared/constants";
import {
  useEventStore,
  ALL_EVENT_TYPES,
  ALL_SEVERITIES,
  type DisasterEvent,
  type EventType,
  type SeverityLevel,
} from "@/store/eventStore";
import { Header } from "@/components/layout/Header";
import { ActiveBadge, SeverityBadge, TypeBadge } from "@/components/event/Badges";
import { formatDate, formatWhen } from "@/lib/format";
import { formatPosition, getEventPosition } from "@/lib/eventPosition";
import { useTranslation } from "@/lib/i18n/useTranslation";
import { EventTypeIcon } from "@/components/event/EventTypeIcon";

function EventCard({ event }: { event: DisasterEvent }) {
  const { t, lang } = useTranslation();
  const typeColor = EVENT_TYPE_COLORS[event.type as EventType] || "#808080";

  return (
    <Link
      href={`/events/${event.id}`}
      className="group flex flex-col rounded-xl border border-gray-700/80 bg-gray-900 p-4 transition-colors hover:border-gray-700 hover:bg-gray-800/40"
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <div
            className="flex h-10 w-10 items-center justify-center rounded-lg"
            style={{ backgroundColor: `${typeColor}20`, color: typeColor }}
          >
            <EventTypeIcon type={event.type} className="h-5 w-5" />
          </div>
          <div className="flex-1">
            <h3 className="font-medium text-white">{event.title}</h3>
            <p className="mt-1 text-sm text-gray-400 line-clamp-2">
              {event.description || t.detail.noDescription}
            </p>
          </div>
        </div>
        <ChevronRight
          className="h-5 w-5 flex-shrink-0 text-gray-500 transition-transform group-hover:translate-x-0.5 group-hover:text-gray-400 rtl:rotate-180"
          aria-hidden="true"
        />
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-1.5 text-sm text-gray-400">
        <div className="flex items-center gap-1">
          <MapPin className="h-4 w-4" aria-hidden="true" />
          <span>
            {event.location.country || formatPosition(getEventPosition(event))}
          </span>
        </div>
        {event.affectedPopulation != null && event.affectedPopulation > 0 && (
          <div className="flex items-center gap-1">
            <Users className="h-4 w-4" aria-hidden="true" />
            <span>{t.detail.affectedCount.replace("{n}", event.affectedPopulation.toLocaleString(lang))}</span>
          </div>
        )}
        <div className="flex items-center gap-1">
          <Clock className="h-4 w-4" aria-hidden="true" />
          <time dateTime={event.startDate} title={formatDate(event.startDate, lang)}>
            {formatWhen(event.startDate, lang)}
          </time>
        </div>
      </div>

      <div className="mt-auto flex flex-wrap items-center gap-2 pt-3">
        <TypeBadge type={event.type} />
        <SeverityBadge severity={event.severity} />
        {event.isActive && <ActiveBadge />}
      </div>
    </Link>
  );
}

function EventsPageContent() {
  const { t } = useTranslation();
  const {
    events,
    isLoading,
    error,
    visibleTypes,
    visibleSeverities,
    toggleEventType,
    toggleSeverity,
    clearFilters,
    setFilter,
  } = useEventStore();

  // Header search navigates to /events?q=...; setFilter refetches
  const query = useSearchParams().get("q")?.trim() || undefined;
  useEffect(() => {
    setFilter({ q: query });
  }, [query, setFilter]);

  const eventTypes = Object.keys(EVENT_TYPE_LABELS) as EventType[];
  const severityLevels: SeverityLevel[] = ["critical", "high", "medium", "low"];
  // Pills show what is visible, matching the sidebar checkboxes (same store)
  const selectedTypes = visibleTypes;
  const selectedSeverities = visibleSeverities;
  const isFiltered =
    visibleTypes.size < ALL_EVENT_TYPES.length ||
    visibleSeverities.size < ALL_SEVERITIES.length;

  return (
    <div className="flex min-h-screen flex-col bg-gray-950">
      <Header />

      <main className="flex-1 px-4 py-6 md:px-6 lg:px-8">
        <div className="mx-auto max-w-6xl">
          <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
            <div>
              <h1 className="text-2xl font-bold text-white">
                {t.events.title}
              </h1>
              <p className="mt-1 text-sm text-gray-400">
                {events.length} {t.events.eventsFound}
                {query && (
                  <>
                    {" · "}&ldquo;{query}&rdquo;{" "}
                    <Link href="/events" className="text-primary-400 hover:underline">
                      ✕
                    </Link>
                  </>
                )}
              </p>
            </div>
            <Link
              href="/"
              className="btn-primary"
            >
              {t.common.viewOnMap}
            </Link>
          </div>

          <div className="mb-6 space-y-3">
            <div
              role="group"
              aria-label={t.sidebar.eventTypes}
              className="-mx-4 flex gap-2 overflow-x-auto px-4 pb-1 md:mx-0 md:flex-wrap md:overflow-visible md:px-0"
            >
              {eventTypes.map((type) => {
                const on = selectedTypes.has(type);
                return (
                  <button
                    key={type}
                    type="button"
                    onClick={() => toggleEventType(type)}
                    aria-pressed={on}
                    className={`flex shrink-0 items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-medium transition-colors ${
                      on
                        ? "border-gray-600 bg-gray-800 text-gray-100 hover:bg-gray-700"
                        : "border-gray-800 text-gray-500 hover:border-gray-700 hover:text-gray-300"
                    }`}
                  >
                    <span
                      aria-hidden="true"
                      className="[&>svg]:h-3.5 [&>svg]:w-3.5"
                      style={{ color: on ? EVENT_TYPE_COLORS[type] : undefined }}
                    >
                      <EventTypeIcon type={type} className="h-5 w-5" />
                    </span>
                    {t.sidebar[type] ?? EVENT_TYPE_LABELS[type]}
                  </button>
                );
              })}
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <span className="me-1 text-xs font-medium text-gray-400">
                {t.sidebar.severity}
              </span>
              {severityLevels.map((severity) => {
                const on = selectedSeverities.has(severity);
                return (
                  <button
                    key={severity}
                    type="button"
                    onClick={() => toggleSeverity(severity)}
                    aria-pressed={on}
                    className={`flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-medium transition-colors ${
                      on
                        ? "border-gray-600 bg-gray-800 text-gray-100 hover:bg-gray-700"
                        : "border-gray-800 text-gray-500 hover:border-gray-700 hover:text-gray-300"
                    }`}
                  >
                    <span
                      aria-hidden="true"
                      className="h-2 w-2 rounded-full"
                      style={{
                        backgroundColor: on ? severityColor(severity) : "rgb(var(--gray-600))",
                      }}
                    />
                    {t.sidebar[severity]}
                  </button>
                );
              })}
              {isFiltered && (
                <button
                  type="button"
                  onClick={clearFilters}
                  className="ms-1 text-xs font-medium text-primary-300 hover:underline"
                >
                  {t.events.clearFilters}
                </button>
              )}
            </div>
          </div>

          {error && (
            <div role="alert" className="mb-6 rounded-lg border border-ember-600/50 bg-ember-700/10 p-4 text-sm text-ember-300">
              Failed to load events: {error}
            </div>
          )}

          {isLoading && events.length === 0 ? (
            <div
              role="status"
              aria-label={t.common.loading}
              className="grid gap-4 md:grid-cols-2 lg:grid-cols-3"
            >
              {Array.from({ length: 6 }, (_, i) => (
                <div
                  key={i}
                  className="h-52 animate-pulse rounded-xl border border-gray-700/80 bg-gray-900"
                />
              ))}
            </div>
          ) : events.length === 0 ? (
            <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-gray-800 py-16 text-center">
              <AlertTriangle className="mb-4 h-10 w-10 text-gray-600" aria-hidden="true" />
              <p className="font-medium text-gray-200">{t.events.noEvents}</p>
              <p className="mt-1 text-sm text-gray-400">
                {t.events.adjustFilters}
              </p>
              {(isFiltered || query) && (
                <div className="mt-5 flex gap-2">
                  {isFiltered && (
                    <button type="button" onClick={clearFilters} className="btn-ghost">
                      {t.events.clearFilters}
                    </button>
                  )}
                  {query && (
                    <Link href="/events" className="btn-ghost">
                      {t.ux.showAll}
                    </Link>
                  )}
                </div>
              )}
            </div>
          ) : (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {events.map((event) => (
                <EventCard key={event.id} event={event} />
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

// useSearchParams() needs a Suspense boundary for static rendering
export default function EventsPage() {
  return (
    <Suspense>
      <EventsPageContent />
    </Suspense>
  );
}
