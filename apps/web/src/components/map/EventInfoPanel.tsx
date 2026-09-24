"use client";

import { Clapperboard, Navigation } from "lucide-react";
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
  const { t } = useTranslation();
  const startBrief = useBriefStore((s) => s.start);
  const routeTo = useRouteStore((s) => s.routeTo);
  const severity = event.severity as SeverityLevel;
  const brief = briefFromEvent(event, t.brief.captions);
  const position = getEventPosition(event);

  return (
    // right-14 keeps the zoom/compass controls (top-right) clickable
    <div className="absolute right-14 top-4 max-h-[calc(100%-2rem)] w-80 overflow-y-auto rounded-lg bg-gray-900/95 p-4 shadow-xl backdrop-blur">
      <div className="mb-2 flex items-start justify-between">
        <h3 className="font-semibold text-white">{event.title}</h3>
        <button onClick={onClose} className="text-gray-400 hover:text-white" aria-label={t.common.close}>
          &times;
        </button>
      </div>
      <p className="mb-3 text-sm text-gray-400">{event.description}</p>
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
            <span className="text-gray-300">{event.affectedPopulation.toLocaleString()}</span>
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
          className="mt-3 flex w-full items-center justify-center gap-2 rounded-md border border-cyan-700 px-3 py-1.5 text-sm font-medium text-cyan-200 hover:bg-cyan-900/40"
        >
          <Navigation className="h-4 w-4" aria-hidden="true" />
          {t.routing.routeHere}
        </button>
      )}
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
