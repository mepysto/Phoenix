"use client";

import Link from "next/link";
import { Bell, ChevronDown, Clapperboard, FileText, HandHeart, MapPin, Navigation, Users, X } from "lucide-react";
import { SeverityBadge, TypeBadge } from "@/components/event/Badges";
import { ConfidenceRing, LifecycleTrack } from "@/components/trust/EventTrust";
import type { ApiDisasterEvent } from "@/lib/api/client";
import { briefFromEvent } from "@/lib/brief";
import { getEventPosition } from "@/lib/eventPosition";
import { placeName } from "@/lib/eventPlace";
import { formatMoment } from "@/lib/format";
import { useTranslation } from "@/lib/i18n/useTranslation";
import { severityColor } from "@/lib/severity";
import { useBriefStore } from "@/store/briefStore";
import { useRouteStore } from "@/store/routeStore";
import { LocalRadio } from "./LocalRadio";
import { NearbyCameras } from "./NearbyCameras";
import { SatellitePasses } from "./SatellitePasses";

interface EventInfoPanelProps {
  event: ApiDisasterEvent;
  onClose: () => void;
}

const SECONDARY =
  "flex flex-1 items-center justify-center gap-2 rounded-lg border border-gray-700 px-3 py-2 text-sm font-medium text-gray-200 hover:bg-gray-800";

/**
 * The selected event (UX plan 5.1): what, where, when and how many people
 * first, then the way to its page, then ways to act; everything else folds.
 */
export function EventInfoPanel({ event, onClose }: EventInfoPanelProps) {
  const { t, lang } = useTranslation();
  const startBrief = useBriefStore((s) => s.start);
  const routeTo = useRouteStore((s) => s.routeTo);
  const brief = briefFromEvent(event, t.brief.captions);
  const position = getEventPosition(event);
  const place = placeName(event);
  const affected = event.affectedPopulation && event.affectedPopulation > 0 ? event.affectedPopulation : null;
  const alertsHref = position
    ? `/alerts?lat=${position.lat.toFixed(2)}&lng=${position.lng.toFixed(2)}&name=${encodeURIComponent(place)}`
    : "/alerts";

  return (
    // right-14 keeps the zoom/compass controls (top-right) clickable
    <section
      aria-label={event.title}
      className="hud-panel absolute right-14 top-4 max-h-[calc(100%-2rem)] w-80 animate-panel-in overflow-y-auto rounded-xl p-4"
    >
      <span
        aria-hidden="true"
        className="absolute inset-y-4 left-0 w-1 rounded-full"
        style={{ backgroundColor: severityColor(event.severity) }}
      />
      <div className="flex items-start justify-between gap-2">
        <div className="flex flex-wrap gap-1.5">
          <SeverityBadge severity={event.severity} />
          <TypeBadge type={event.type} />
        </div>
        <button
          onClick={onClose}
          className="-mr-1 -mt-1 rounded-md p-1 text-gray-400 hover:bg-gray-800 hover:text-white"
          aria-label={t.common.close}
        >
          <X className="h-4 w-4" aria-hidden="true" />
        </button>
      </div>
      <h3 className="mt-2 text-base font-semibold leading-snug text-white">{event.title}</h3>

      <dl className="mt-3 space-y-1.5 text-sm text-gray-200">
        <div className="flex items-start gap-2">
          <dt className="sr-only">{t.events.location}</dt>
          <MapPin className="mt-0.5 h-4 w-4 shrink-0 text-gray-400" aria-hidden="true" />
          <dd>{place}</dd>
        </div>
        <div className="flex items-start gap-2 text-gray-300">
          <dt className="sr-only">{t.detail.startDate}</dt>
          <dd>
            <time dateTime={event.startDate}>{formatMoment(event.startDate, lang)}</time>
            {event.trust && <> · {t.trust.stages[event.trust.lifecycle]}</>}
          </dd>
        </div>
        {affected !== null && (
          <div className="flex items-start gap-2">
            <dt className="sr-only">{t.events.affected}</dt>
            <Users className="mt-0.5 h-4 w-4 shrink-0 text-gray-400" aria-hidden="true" />
            <dd>{t.detail.affectedCount.replace("{n}", affected.toLocaleString(lang))}</dd>
          </div>
        )}
      </dl>

      <Link href={`/events/${event.id}`} className="btn-primary mt-4 w-full">
        <FileText className="h-4 w-4" aria-hidden="true" />
        {t.ux.viewDetails}
      </Link>
      <div className="mt-2 flex gap-2">
        <Link href={`/connect?event=${event.id}`} className={SECONDARY}>
          <HandHeart className="h-4 w-4" aria-hidden="true" />
          {t.connect.offerHelp}
        </Link>
        <Link href={alertsHref} className={SECONDARY}>
          <Bell className="h-4 w-4" aria-hidden="true" />
          {t.alerts.watch}
        </Link>
      </div>

      <details className="group mt-3 rounded-lg border border-gray-700/80">
        <summary className="flex cursor-pointer list-none items-center justify-between px-3 py-2 text-sm font-medium text-gray-300 hover:text-white">
          {t.ux.moreAboutEvent}
          <ChevronDown className="h-4 w-4 transition-transform group-open:rotate-180" aria-hidden="true" />
        </summary>
        <div className="space-y-3 border-t border-gray-700/80 p-3">
          {event.trust && (
            <div className="space-y-3">
              <ConfidenceRing trust={event.trust} size={40} />
              <LifecycleTrack stage={event.trust.lifecycle} compact />
            </div>
          )}
          {brief && (
            <button
              type="button"
              onClick={() => {
                onClose();
                startBrief(brief);
              }}
              className={`${SECONDARY} w-full`}
            >
              <Clapperboard className="h-4 w-4" aria-hidden="true" />
              {t.brief.play}
            </button>
          )}
          {position && (
            <button
              type="button"
              onClick={() => routeTo({ lat: position.lat, lng: position.lng, label: event.title })}
              className={`${SECONDARY} w-full`}
            >
              <Navigation className="h-4 w-4" aria-hidden="true" />
              {t.routing.routeHere}
            </button>
          )}
          {position && <SatellitePasses lat={position.lat} lng={position.lng} />}
          {position && <NearbyCameras lat={position.lat} lng={position.lng} />}
          {position && <LocalRadio lat={position.lat} lng={position.lng} />}
        </div>
      </details>
    </section>
  );
}
