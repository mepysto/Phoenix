"use client";

import Link from "next/link";
import { ChevronRight, MapPin, Users } from "lucide-react";
import type { ApiDisasterEvent } from "@/lib/api/client";
import { SeverityBadge } from "@/components/event/Badges";
import { EventTypeIcon } from "@/components/event/EventTypeIcon";
import { compactNumber, formatDate, formatWhen } from "@/lib/format";
import { placeName } from "@/lib/eventPlace";
import { useTranslation } from "@/lib/i18n/useTranslation";
import { severityColor } from "@/lib/severity";
import type { EventType } from "@phoenix/shared/types";

const BOILERPLATE = /^no description available\.?$/i;

/** The description, unless it only repeats the title and place (USGS does) */
export function usefulDescription(event: ApiDisasterEvent, place: string): string | null {
  const text = event.description?.trim();
  if (!text || BOILERPLATE.test(text)) return null;
  if (text.includes(place) || text.includes(event.title)) return null;
  return text;
}

/**
 * One disaster per line (UX plan 5.2): severity as a coloured edge and a
 * badge, then type, title, place, people affected and when it began.
 */
export function EventRow({ event }: { event: ApiDisasterEvent }) {
  const { t, lang } = useTranslation();
  const place = placeName(event);
  const description = usefulDescription(event, place);
  const affected = event.affectedPopulation && event.affectedPopulation > 0 ? event.affectedPopulation : null;
  const typeLabel = t.sidebar[event.type as EventType] ?? event.type;

  return (
    <li>
      <Link
        href={`/events/${event.id}`}
        className="group relative flex items-start gap-3 overflow-hidden rounded-xl border border-gray-700/80 bg-gray-900 py-3 pe-3 ps-5 transition-colors hover:border-gray-600 hover:bg-gray-800/50"
      >
        <span
          aria-hidden="true"
          className="absolute inset-y-0 start-0 w-1.5"
          style={{ backgroundColor: severityColor(event.severity) }}
        />
        <div className="min-w-0 flex-1 md:grid md:grid-cols-[10rem_minmax(0,1fr)_11rem_5rem_7rem] md:items-center md:gap-4">
          <div className="flex items-center gap-2 md:block">
            <SeverityBadge severity={event.severity} />
            <span className="flex items-center gap-1.5 text-sm text-gray-300 md:mt-1.5">
              <EventTypeIcon type={event.type} className="h-4 w-4 text-gray-400" />
              {typeLabel}
            </span>
          </div>
          <div className="mt-1.5 min-w-0 md:mt-0">
            <p className="font-medium text-white group-hover:text-primary-100">{event.title}</p>
            {description && <p className="mt-0.5 line-clamp-1 text-sm text-gray-400">{description}</p>}
          </div>
          <p className="mt-1 flex min-w-0 items-center gap-1.5 text-sm text-gray-300 md:mt-0">
            <MapPin className="h-4 w-4 shrink-0 text-gray-400 md:hidden" aria-hidden="true" />
            <span className="truncate" title={place}>
              {place}
            </span>
          </p>
          <p className="mt-1 flex items-center gap-1.5 text-sm tabular-nums text-gray-300 md:mt-0">
            {affected !== null && (
              <>
                <Users className="h-4 w-4 shrink-0 text-gray-400" aria-hidden="true" />
                <span title={t.detail.affectedCount.replace("{n}", affected.toLocaleString(lang))}>
                  {compactNumber(affected, lang)}
                </span>
              </>
            )}
          </p>
          <p className="mt-1 text-sm text-gray-400 md:mt-0 md:text-end">
            <time dateTime={event.startDate} title={formatDate(event.startDate, lang)}>
              {formatWhen(event.startDate, lang)}
            </time>
          </p>
        </div>
        <ChevronRight
          className="mt-1 h-5 w-5 shrink-0 text-gray-500 transition-transform group-hover:translate-x-0.5 group-hover:text-gray-300 md:mt-0 md:self-center rtl:rotate-180"
          aria-hidden="true"
        />
      </Link>
    </li>
  );
}
