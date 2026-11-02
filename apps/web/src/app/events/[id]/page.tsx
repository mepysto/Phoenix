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
  HandHeart,
  LayoutGrid,
  Bell,
} from "lucide-react";
import { EVENT_TYPE_COLORS } from "@phoenix/shared/constants";
import {
  APIError,
  eventsAPI,
  fetchEventDamage,
  type ApiDamageSummary,
  type ApiDisasterEventDetail,
  type EventType,
} from "@/lib/api/client";
import { Header } from "@/components/layout/Header";
import { ActiveBadge, SeverityBadge, TypeBadge } from "@/components/event/Badges";
import { formatDate, formatDateTime, formatRelative } from "@/lib/format";
import { useTranslation } from "@/lib/i18n/useTranslation";
import { ConfidenceRing, LifecycleTrack } from "@/components/trust/EventTrust";
import { SitrepPanel } from "@/components/event/SitrepPanel";
import { DamagePanel } from "@/components/event/DamagePanel";
import { EventCommunity } from "@/components/event/EventCommunity";

const BeforeAfterCompare = dynamic(
  () => import("@/components/event/BeforeAfterCompare").then((m) => m.BeforeAfterCompare),
  { ssr: false, loading: () => <div className="h-96 animate-pulse rounded-xl bg-gray-900" /> },
);

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
        <div className="text-xs text-gray-400">
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
  // Shared by the damage panel and the situation report
  const [damage, setDamage] = useState<ApiDamageSummary | null>(null);
  const [damageFailed, setDamageFailed] = useState(false);
  useEffect(() => {
    if (!eventId) return;
    const controller = new AbortController();
    setDamage(null);
    setDamageFailed(false);
    fetchEventDamage(eventId, controller.signal)
      .then(setDamage)
      .catch(() => {
        if (!controller.signal.aborted) setDamageFailed(true);
      });
    return () => controller.abort();
  }, [eventId]);
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

  return (
    <div className="flex min-h-screen flex-col bg-gray-950">
      <Header />

      <main className="flex-1 px-4 py-6 md:px-6 lg:px-8">
        <div className="mx-auto max-w-6xl">
          <Link
            href="/events"
            className="mb-6 inline-flex items-center gap-2 text-sm text-gray-400 hover:text-white transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
            {t.detail.back}
          </Link>

          <div className="grid gap-6 lg:grid-cols-3">
            <div className="min-w-0 space-y-6 lg:col-span-2">
              <div className="rounded-xl border border-gray-800 bg-gray-900 p-6">
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
                    <div className="mb-2 flex flex-wrap items-center gap-2">
                      <TypeBadge type={event.type} />
                      <SeverityBadge severity={event.severity} />
                      {event.isActive && <ActiveBadge />}
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

                {/* Phones and tablets: the actions sit up here, not after every panel */}
                <nav
                  aria-label={t.ux.actions}
                  className="mt-5 grid grid-cols-2 gap-2 sm:grid-cols-4 lg:hidden"
                >
                  <Link href={`/?event=${event.id}`} className="btn-primary px-3">
                    <Globe className="h-4 w-4" aria-hidden="true" />
                    {t.common.viewOnMap}
                  </Link>
                  <Link href={`/connect?event=${event.id}`} className="btn-ghost px-3">
                    <HandHeart className="h-4 w-4" aria-hidden="true" />
                    {t.connect.offerHelp}
                  </Link>
                  <Link href={`/plan?event=${event.id}`} className="btn-ghost px-3">
                    <LayoutGrid className="h-4 w-4" aria-hidden="true" />
                    {t.ux.plan}
                  </Link>
                  {position && (
                    <Link
                      href={`/alerts?lat=${position.lat.toFixed(2)}&lng=${position.lng.toFixed(2)}&name=${encodeURIComponent(event.location.country || event.title)}`}
                      className="btn-ghost px-3"
                    >
                      <Bell className="h-4 w-4" aria-hidden="true" />
                      {t.alerts.watch}
                    </Link>
                  )}
                </nav>
              </div>

              <div className="rounded-xl border border-gray-800 bg-gray-900 overflow-hidden">
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

              <SitrepPanel event={event} damage={damage} />

              <DamagePanel data={damage} failed={damageFailed} />

              {position && (
                <BeforeAfterCompare
                  lat={position.lat}
                  lng={position.lng}
                  type={event.type}
                  startDate={event.startDate}
                />
              )}

              {event.sources && event.sources.length > 0 && (
                <div className="rounded-xl border border-gray-800 bg-gray-900 p-6">
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
              {event.trust && (
                <section className="rounded-xl border border-gray-800 bg-gray-900 p-6" aria-labelledby="trust-title">
                  <h2 id="trust-title" className="mb-4 text-lg font-semibold text-white">
                    {t.trust.title}
                  </h2>
                  <ConfidenceRing trust={event.trust} size={56} />
                  <div className="mt-5">
                    <LifecycleTrack stage={event.trust.lifecycle} />
                  </div>
                </section>
              )}
              <div className="rounded-xl border border-gray-800 bg-gray-900 p-6">
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
                    value={formatDate(event.startDate, lang)}
                  />
                  {event.endDate && (
                    <InfoRow
                      icon={<Calendar className="h-4 w-4" />}
                      label={t.detail.endDate}
                      value={formatDate(event.endDate, lang)}
                    />
                  )}
                  <InfoRow
                    icon={<Clock className="h-4 w-4" />}
                    label={t.detail.lastUpdated}
                    value={`${formatDateTime(event.updatedAt, lang)} · ${formatRelative(event.updatedAt, lang)}`}
                  />
                </div>
              </div>

              <EventCommunity eventId={event.id} />
              <div className="rounded-xl border border-gray-800 bg-gray-900 p-6">
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
                  <Link
                    href={`/connect?event=${event.id}`}
                    className="flex w-full items-center justify-center gap-2 rounded-lg border border-gray-700 px-4 py-2.5 text-sm font-medium text-gray-200 transition-colors hover:bg-gray-800"
                  >
                    {t.connect.offerHelp}
                  </Link>
                  <Link
                    href={`/plan?event=${event.id}`}
                    className="flex w-full items-center justify-center gap-2 rounded-lg border border-gray-700 px-4 py-2.5 text-sm font-medium text-gray-200 transition-colors hover:bg-gray-800"
                  >
                    {t.plan.open}
                  </Link>
                  <Link
                    href={`/challenges?event=${event.id}`}
                    className="flex w-full items-center justify-center gap-2 rounded-lg border border-gray-700 px-4 py-2.5 text-sm font-medium text-gray-200 transition-colors hover:bg-gray-800"
                  >
                    {t.challenges.title}
                  </Link>
                  {position && (
                    <Link
                      href={`/alerts?lat=${position.lat.toFixed(2)}&lng=${position.lng.toFixed(2)}&name=${encodeURIComponent(event.location.country || event.title)}`}
                      className="flex w-full items-center justify-center gap-2 rounded-lg border border-gray-700 px-4 py-2.5 text-sm font-medium text-gray-200 transition-colors hover:bg-gray-800"
                    >
                      {t.alerts.watch}
                    </Link>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
