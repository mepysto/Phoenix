"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { formatPosition, getEventPosition } from "@/lib/eventPosition";
import dynamic from "next/dynamic";
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
  ArrowLeft,
  Calendar,
  Globe,
} from "lucide-react";
import { EVENT_TYPE_COLORS, SEVERITY_COLORS } from "@phoenix/shared/constants";
import {
  APIError,
  eventsAPI,
  type ApiDisasterEventDetail,
  type EventType,
  type SeverityLevel,
} from "@/lib/api/client";
import { Header } from "@/components/layout/Header";
import { useTranslation } from "@/lib/i18n/useTranslation";

const MiniMap = dynamic(() => import("@/components/map/MiniMap"), {
  ssr: false,
  loading: () => <div className="h-full w-full bg-gray-800 animate-pulse" />,
});

// Types without a dedicated icon fall back to `other`
const EVENT_ICONS: Partial<Record<EventType, React.ReactNode>> & {
  other: React.ReactNode;
} = {
  earthquake: <Mountain className="h-6 w-6" />,
  flood: <Droplets className="h-6 w-6" />,
  wildfire: <Flame className="h-6 w-6" />,
  hurricane: <Wind className="h-6 w-6" />,
  tsunami: <Droplets className="h-6 w-6" />,
  volcano: <Mountain className="h-6 w-6" />,
  war: <Skull className="h-6 w-6" />,
  pollution: <Factory className="h-6 w-6" />,
  drought: <Sun className="h-6 w-6" />,
  other: <AlertTriangle className="h-6 w-6" />,
};

function InfoRow({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string | React.ReactNode;
}) {
  return (
    <div className="flex items-start gap-3 py-3 border-b border-gray-800 last:border-0">
      <div className="text-gray-500">{icon}</div>
      <div className="flex-1">
        <div className="text-xs text-gray-500 uppercase tracking-wide">
          {label}
        </div>
        <div className="mt-0.5 text-sm text-gray-200">{value}</div>
      </div>
    </div>
  );
}

export default function EventDetailPage() {
  const params = useParams();
  const eventId = params.id as string;
  const { t, lang } = useTranslation();

  const [event, setEvent] = useState<ApiDisasterEventDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  // HTTP status of a failed load (404 = no such event); the message is translated at render
  const [errorStatus, setErrorStatus] = useState<number | null>(null);

  useEffect(() => {
    async function fetchEvent() {
      try {
        setIsLoading(true);
        setErrorStatus(null);
        const data = await eventsAPI.get(eventId);
        setEvent(data);
      } catch (err) {
        setErrorStatus(err instanceof APIError ? err.statusCode : 0);
      } finally {
        setIsLoading(false);
      }
    }

    if (eventId) {
      fetchEvent();
    }
  }, [eventId]);

  if (isLoading) {
    return (
      <div className="flex min-h-screen flex-col bg-gray-950">
        <Header />
        <div className="flex flex-1 items-center justify-center">
          <div className="text-center">
            <div className="mb-4 h-10 w-10 animate-spin rounded-full border-4 border-primary-500 border-t-transparent mx-auto" />
            <p className="text-gray-400">{t.detail.loading}</p>
          </div>
        </div>
      </div>
    );
  }

  if (errorStatus !== null || !event) {
    return (
      <div className="flex min-h-screen flex-col bg-gray-950">
        <Header />
        <div className="flex flex-1 items-center justify-center">
          <div className="text-center">
            <AlertTriangle className="h-12 w-12 text-red-500 mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-white mb-2">
              {errorStatus === null || errorStatus === 404 ? t.detail.notFound : t.errors.errorTitle}
            </h2>
            <p className="text-gray-400 mb-4">
              {errorStatus === null || errorStatus === 404 ? t.detail.notFoundBody : t.errors.errorBody}
            </p>
            <Link
              href="/events"
              className="inline-flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 transition-colors"
            >
              <ArrowLeft className="h-4 w-4" />
              {t.detail.back}
            </Link>
          </div>
        </div>
      </div>
    );
  }

  const typeColor = EVENT_TYPE_COLORS[event.type as EventType] || "#808080";
  const position = getEventPosition(event);
  const severityColor =
    SEVERITY_COLORS[event.severity as SeverityLevel] || "#808080";

  return (
    <div className="flex min-h-screen flex-col bg-gray-950">
      <Header />

      <main className="flex-1 px-4 py-6 md:px-6 lg:px-8">
        <div className="mx-auto max-w-4xl">
          <Link
            href="/events"
            className="mb-6 inline-flex items-center gap-2 text-sm text-gray-400 hover:text-white transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
            {t.detail.back}
          </Link>

          <div className="grid gap-6 lg:grid-cols-3">
            <div className="lg:col-span-2 space-y-6">
              <div className="rounded-lg border border-gray-800 bg-gray-900 p-6">
                <div className="flex items-start gap-4">
                  <div
                    className="flex h-14 w-14 items-center justify-center rounded-xl"
                    style={{
                      backgroundColor: `${typeColor}20`,
                      color: typeColor,
                    }}
                  >
                    {EVENT_ICONS[event.type as EventType] ?? EVENT_ICONS.other}
                  </div>
                  <div className="flex-1">
                    <div className="flex flex-wrap items-center gap-2 mb-2">
                      <span
                        className="rounded-full px-2.5 py-0.5 text-xs font-medium"
                        style={{
                          backgroundColor: `${typeColor}20`,
                          color: typeColor,
                        }}
                      >
                        {t.sidebar[event.type as EventType] ?? event.type}
                      </span>
                      <span
                        className="rounded-full px-2.5 py-0.5 text-xs font-medium text-white"
                        style={{ backgroundColor: severityColor }}
                      >
                        {t.sidebar[event.severity as SeverityLevel] ?? event.severity}
                      </span>
                      {event.isActive && (
                        <span className="rounded-full bg-green-900/50 px-2.5 py-0.5 text-xs font-medium text-green-400">
                          {t.detail.active}
                        </span>
                      )}
                    </div>
                    <h1 className="text-2xl font-bold text-white">
                      {event.title}
                    </h1>
                  </div>
                </div>

                {event.description && (
                  <p className="mt-4 text-gray-300 leading-relaxed">
                    {event.description}
                  </p>
                )}
              </div>

              <div className="rounded-lg border border-gray-800 bg-gray-900 overflow-hidden">
                <div className="h-64 lg:h-80">
                  {position ? (
                    <MiniMap lat={position.lat} lng={position.lng} />
                  ) : (
                    <div className="flex h-full items-center justify-center text-sm text-gray-500">
                      {t.detail.locationUnavailable}
                    </div>
                  )}
                </div>
              </div>

              {event.sources && event.sources.length > 0 && (
                <div className="rounded-lg border border-gray-800 bg-gray-900 p-6">
                  <h2 className="text-lg font-semibold text-white mb-4">
                    {t.detail.dataSources}
                  </h2>
                  <div className="space-y-3">
                    {event.sources.map((source) => (
                      <div
                        key={source.id}
                        className="flex items-center justify-between rounded-lg bg-gray-800/50 px-4 py-3"
                      >
                        <div className="flex items-center gap-3">
                          <Globe className="h-5 w-5 text-gray-400" />
                          <div>
                            <div className="font-medium text-white">
                              {source.name}
                            </div>
                            <div className="text-xs text-gray-500 capitalize">
                              {source.type.replace("_", " ")}
                            </div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <div className="space-y-6">
              <div className="rounded-lg border border-gray-800 bg-gray-900 p-6">
                <h2 className="text-lg font-semibold text-white mb-4">
                  {t.detail.details}
                </h2>
                <div>
                  <InfoRow
                    icon={<MapPin className="h-4 w-4" />}
                    label={t.detail.location}
                    value={
                      <>
                        {event.location.country && (
                          <div>{event.location.country}</div>
                        )}
                        <div className="text-xs text-gray-500">
                          {formatPosition(position, 4)}
                        </div>
                      </>
                    }
                  />
                  {event.affectedPopulation != null && event.affectedPopulation > 0 && (
                    <InfoRow
                      icon={<Users className="h-4 w-4" />}
                      label={t.detail.affectedPopulation}
                      value={event.affectedPopulation.toLocaleString(lang)}
                    />
                  )}
                  <InfoRow
                    icon={<Calendar className="h-4 w-4" />}
                    label={t.detail.startDate}
                    value={new Date(event.startDate).toLocaleDateString(lang, { year: "numeric", month: "long", day: "numeric" })}
                  />
                  {event.endDate && (
                    <InfoRow
                      icon={<Calendar className="h-4 w-4" />}
                      label={t.detail.endDate}
                      value={new Date(event.endDate).toLocaleDateString(lang, { year: "numeric", month: "long", day: "numeric" })}
                    />
                  )}
                  <InfoRow
                    icon={<Clock className="h-4 w-4" />}
                    label={t.detail.lastUpdated}
                    value={new Date(event.updatedAt).toLocaleString(lang)}
                  />
                </div>
              </div>

              <div className="rounded-lg border border-gray-800 bg-gray-900 p-6">
                <h2 className="text-lg font-semibold text-white mb-4">
                  {t.detail.actions}
                </h2>
                <div className="space-y-3">
                  <Link
                    href={`/?event=${event.id}`}
                    className="flex items-center justify-center gap-2 rounded-lg bg-primary-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-primary-700 transition-colors w-full"
                  >
                    <Globe className="h-4 w-4" />
                    {t.common.viewOnMap}
                  </Link>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
