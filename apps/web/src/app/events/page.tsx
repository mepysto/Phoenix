"use client";

import { Suspense, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import {
  AlertTriangle,
  Droplets,
  Flame,
  Wind,
  Mountain,
  Skull,
  Factory,
  Sun,
  MapPin,
  Users,
  Clock,
  ChevronRight,
} from "lucide-react";
import {
  EVENT_TYPE_LABELS,
  EVENT_TYPE_COLORS,
  SEVERITY_COLORS,
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
import { formatPosition, getEventPosition } from "@/lib/eventPosition";
import { useTranslation } from "@/lib/i18n/useTranslation";

// Types without a dedicated icon fall back to `other`
const EVENT_ICONS: Partial<Record<EventType, React.ReactNode>> & {
  other: React.ReactNode;
} = {
  earthquake: <Mountain className="h-5 w-5" />,
  flood: <Droplets className="h-5 w-5" />,
  wildfire: <Flame className="h-5 w-5" />,
  hurricane: <Wind className="h-5 w-5" />,
  tsunami: <Droplets className="h-5 w-5" />,
  volcano: <Mountain className="h-5 w-5" />,
  war: <Skull className="h-5 w-5" />,
  pollution: <Factory className="h-5 w-5" />,
  drought: <Sun className="h-5 w-5" />,
  other: <AlertTriangle className="h-5 w-5" />,
};

function EventCard({ event }: { event: DisasterEvent }) {
  const typeColor = EVENT_TYPE_COLORS[event.type as EventType] || "#808080";
  const severityColor =
    SEVERITY_COLORS[event.severity as SeverityLevel] || "#808080";

  return (
    <Link
      href={`/events/${event.id}`}
      className="block rounded-lg border border-gray-800 bg-gray-900 p-4 hover:border-gray-700 hover:bg-gray-800/50 transition-all"
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <div
            className="flex h-10 w-10 items-center justify-center rounded-lg"
            style={{ backgroundColor: `${typeColor}20`, color: typeColor }}
          >
            {EVENT_ICONS[event.type as EventType] ?? EVENT_ICONS.other}
          </div>
          <div className="flex-1">
            <h3 className="font-medium text-white">{event.title}</h3>
            <p className="mt-1 text-sm text-gray-400 line-clamp-2">
              {event.description || "No description available"}
            </p>
          </div>
        </div>
        <ChevronRight className="h-5 w-5 text-gray-600 flex-shrink-0" />
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-4 text-sm text-gray-400">
        <div className="flex items-center gap-1">
          <MapPin className="h-4 w-4" />
          <span>
            {event.location.country || formatPosition(getEventPosition(event))}
          </span>
        </div>
        {event.affectedPopulation && (
          <div className="flex items-center gap-1">
            <Users className="h-4 w-4" />
            <span>{event.affectedPopulation.toLocaleString()} affected</span>
          </div>
        )}
        <div className="flex items-center gap-1">
          <Clock className="h-4 w-4" />
          <span>{new Date(event.startDate).toLocaleDateString()}</span>
        </div>
      </div>

      <div className="mt-3 flex items-center gap-2">
        <span
          className="rounded-full px-2 py-0.5 text-xs font-medium"
          style={{ backgroundColor: `${typeColor}20`, color: typeColor }}
        >
          {EVENT_TYPE_LABELS[event.type as EventType]}
        </span>
        <span
          className="rounded-full px-2 py-0.5 text-xs font-medium text-white"
          style={{ backgroundColor: severityColor }}
        >
          {event.severity.toUpperCase()}
        </span>
        {event.isActive && (
          <span className="rounded-full bg-green-900/50 px-2 py-0.5 text-xs font-medium text-green-400">
            Active
          </span>
        )}
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
          <div className="mb-6 flex items-center justify-between">
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
              className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 transition-colors"
            >
              {t.common.viewOnMap}
            </Link>
          </div>

          <div className="mb-6 flex flex-wrap gap-2">
            <div className="flex flex-wrap gap-2">
              {eventTypes.map((type) => (
                <button
                  key={type}
                  onClick={() => toggleEventType(type)}
                  aria-pressed={selectedTypes.has(type)}
                  className={`flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-medium transition-colors ${
                    selectedTypes.has(type)
                      ? "bg-primary-600 text-white"
                      : "bg-gray-800 text-gray-300 hover:bg-gray-700"
                  }`}
                >
                  <span
                    style={{
                      color: selectedTypes.has(type)
                        ? "white"
                        : EVENT_TYPE_COLORS[type],
                    }}
                  >
                    {EVENT_ICONS[type] ?? EVENT_ICONS.other}
                  </span>
                  {EVENT_TYPE_LABELS[type]}
                </button>
              ))}
            </div>
            <div className="h-6 w-px bg-gray-700" />
            <div className="flex flex-wrap gap-2">
              {severityLevels.map((severity) => (
                <button
                  key={severity}
                  onClick={() => toggleSeverity(severity)}
                  aria-pressed={selectedSeverities.has(severity)}
                  className={`rounded-full px-3 py-1.5 text-xs font-medium transition-colors ${
                    selectedSeverities.has(severity)
                      ? "text-white"
                      : "bg-gray-800 text-gray-300 hover:bg-gray-700"
                  }`}
                  style={
                    selectedSeverities.has(severity)
                      ? { backgroundColor: SEVERITY_COLORS[severity] }
                      : {}
                  }
                >
                  {severity.charAt(0).toUpperCase() + severity.slice(1)}
                </button>
              ))}
            </div>
            {isFiltered && (
              <button
                onClick={clearFilters}
                className="rounded-full bg-gray-800 px-3 py-1.5 text-xs font-medium text-gray-300 hover:bg-gray-700 transition-colors"
              >
                {t.events.clearFilters}
              </button>
            )}
          </div>

          {error && (
            <div className="mb-6 rounded-lg bg-red-900/50 p-4 text-sm text-red-200">
              Failed to load events: {error}
            </div>
          )}

          {isLoading && events.length === 0 ? (
            <div className="flex items-center justify-center py-20">
              <div className="text-center">
                <div className="mb-4 h-10 w-10 animate-spin rounded-full border-4 border-primary-500 border-t-transparent mx-auto" />
                <p className="text-gray-400">{t.common.loading}</p>
              </div>
            </div>
          ) : events.length === 0 ? (
            <div className="flex items-center justify-center py-20">
              <div className="text-center">
                <AlertTriangle className="h-12 w-12 text-gray-600 mx-auto mb-4" />
                <p className="text-gray-400">{t.events.noEvents}</p>
                <p className="text-sm text-gray-500 mt-1">
                  {t.events.adjustFilters}
                </p>
              </div>
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
