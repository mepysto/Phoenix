"use client";

import Link from "next/link";
import { Clapperboard, FileText, Navigation, X } from "lucide-react";
import { ConfidenceRing, LifecycleTrack } from "@/components/trust/EventTrust";
import { SEVERITY_COLORS } from "@phoenix/shared/constants";
import type { ApiDisasterEvent, SeverityLevel } from "@/lib/api/client";
import { briefFromEvent } from "@/lib/brief";
import { formatPosition, getEventPosition } from "@/lib/eventPosition";
import { useTranslation } from "@/lib/i18n/useTranslation";
import { useBriefStore } from "@/store/briefStore";
import { useRouteStore } from "@/store/routeStore";
import { LocalRadio } from "./LocalRadio";
import { NearbyCameras } from "./NearbyCameras";
import { SatellitePasses } from "./SatellitePasses";

interface EventInfoPanelProps {
  event: ApiDisasterEvent;
  onClose: () => void;
}

/** Card for the selected event, with a button to play its Disaster Brief */
export function EventInfoPanel({ event, onClose }: EventInfoPanelProps) {
  const { t, lang } = useTranslation();
  const startBrief = useBriefStore((s) => s.start);
  const routeTo = useRouteStore((s) => s.routeTo);
  const severity = event.severity as SeverityLevel;
  const brief = briefFromEvent(event, t.brief.captions);
  const position = getEventPosition(event);

  return (
    // right-14 keeps the zoom/compass controls (top-right) clickable
    <div className="hud-panel absolute right-14 top-4 max-h-[calc(100%-2rem)] w-80 animate-panel-in overflow-y-auto rounded-xl p-4">
      {/* Severity edge: the one place the card carries the event's colour */}
      <span
        aria-hidden="true"
        className="absolute inset-y-4 left-0 w-0.5 rounded-full"
        style={{ backgroundColor: SEVERITY_COLORS[severity] }}
      />
      <div className="mb-2 flex items-start justify-between gap-2">
        <h3 className="font-semibold leading-snug text-white">{event.title}</h3>
        <button
          onClick={onClose}
          className="-mr-1 -mt-1 rounded-md p-1 text-gray-400 hover:bg-gray-800 hover:text-white"
          aria-label={t.common.close}
        >
          <X className="h-4 w-4" aria-hidden="true" />
        </button>
      </div>
      {event.description && <p className="mb-3 line-clamp-3 text-sm text-gray-400">{event.description}</p>}
      {event.trust && (
        <div className="mb-3 space-y-3 rounded-lg border border-gray-800 bg-gray-950/50 p-3">
          <ConfidenceRing trust={event.trust} size={40} />
          <LifecycleTrack stage={event.trust.lifecycle} compact />
        </div>
      )}
      <div className="space-y-2 text-sm">
        <div className="flex justify-between">
          <span className="text-gray-500">{t.events.location}</span>
          <span className="text-gray-300">
            {event.location.country || formatPosition(position)}
          </span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-500">{t.events.severity}</span>
          <span
            className="rounded-full px-2 py-0.5 text-xs font-medium text-white"
            style={{ backgroundColor: SEVERITY_COLORS[severity] }}
          >
            {t.sidebar[severity]}
          </span>
        </div>
        {event.affectedPopulation != null && event.affectedPopulation > 0 && (
          <div className="flex justify-between">
            <span className="text-gray-500">{t.events.affected}</span>
            <span className="text-gray-300">{event.affectedPopulation.toLocaleString(lang)}</span>
          </div>
        )}
      </div>
      {position && <SatellitePasses lat={position.lat} lng={position.lng} />}
      {position && <NearbyCameras lat={position.lat} lng={position.lng} />}
      {position && <LocalRadio lat={position.lat} lng={position.lng} />}
      {position && (
        <button
          type="button"
          onClick={() => routeTo({ lat: position.lat, lng: position.lng, label: event.title })}
          className="mt-3 flex w-full items-center justify-center gap-2 rounded-md border border-primary-700 px-3 py-1.5 text-sm font-medium text-primary-200 hover:bg-primary-900/40"
        >
          <Navigation className="h-4 w-4" aria-hidden="true" />
          {t.routing.routeHere}
        </button>
      )}
      <Link
        href={`/events/${event.id}`}
        className="mt-3 flex w-full items-center justify-center gap-2 rounded-md border border-gray-700 px-3 py-1.5 text-sm font-medium text-gray-200 hover:bg-gray-800"
      >
        <FileText className="h-4 w-4" aria-hidden="true" />
        {t.sitrep.title}
      </Link>
      {brief && (
        <button
          type="button"
          onClick={() => {
            onClose();
            startBrief(brief);
          }}
          className="mt-3 flex w-full items-center justify-center gap-2 rounded-md bg-primary-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-primary-500"
        >
          <Clapperboard className="h-4 w-4" aria-hidden="true" />
          {t.brief.play}
        </button>
      )}
    </div>
  );
}
