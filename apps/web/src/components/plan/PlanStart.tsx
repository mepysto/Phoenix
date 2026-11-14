"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Map as MapIcon, Search } from "lucide-react";
import { SeverityBadge } from "@/components/event/Badges";
import { EventTypeIcon } from "@/components/event/EventTypeIcon";
import { eventsAPI, type ApiDisasterEvent, type ApiPlace } from "@/lib/api/client";
import { PlaceSearch } from "@/components/ui/PlaceSearch";
import { placeName } from "@/lib/eventPlace";
import { useTranslation } from "@/lib/i18n/useTranslation";

const SHOWN = 8;

/**
 * Before planning: which disaster is this site for? (UX plan A-02). Picking
 * one opens the planner at its location; an empty map stays possible.
 */
export function PlanStart({ onBlank, onPlace }: { onBlank: () => void; onPlace: (place: ApiPlace) => void }) {
  const { t } = useTranslation();
  const [query, setQuery] = useState("");
  const [events, setEvents] = useState<ApiDisasterEvent[] | null>(null);

  useEffect(() => {
    const controller = { cancelled: false };
    const timer = setTimeout(() => {
      eventsAPI
        .list({ isActive: true, q: query.trim() || undefined }, SHOWN, 0, "importance")
        .then((r) => !controller.cancelled && setEvents(r.data))
        .catch(() => !controller.cancelled && setEvents([]));
    }, 250);
    return () => {
      controller.cancelled = true;
      clearTimeout(timer);
    };
  }, [query]);

  return (
    <main className="flex-1 overflow-y-auto px-4 py-8 md:px-6">
      <div className="mx-auto max-w-3xl">
        <h1 className="text-3xl font-semibold tracking-tight text-white">{t.ux.planStartTitle}</h1>
        <p className="mt-2 text-gray-300">{t.ux.planStartIntro}</p>

        <div className="relative mt-6">
          <Search className="pointer-events-none absolute start-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" aria-hidden="true" />
          <label htmlFor="plan-find" className="sr-only">
            {t.events.searchLabel}
          </label>
          <input
            id="plan-find"
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={t.events.searchLabel}
            className="field !ps-9"
          />
        </div>

        <ul className="mt-4 space-y-2" aria-busy={events === null}>
          {(events ?? []).map((event) => (
            <li key={event.id}>
              <Link
                href={`/plan?event=${event.id}`}
                className="flex items-center gap-3 rounded-xl border border-gray-700/80 bg-gray-900 px-4 py-3 hover:border-primary-400/60"
              >
                <EventTypeIcon type={event.type} className="h-5 w-5 shrink-0 text-gray-300" />
                <span className="min-w-0 flex-1">
                  <span className="block font-medium text-white">{event.title}</span>
                  <span className="block text-sm text-gray-400">{placeName(event)}</span>
                </span>
                <SeverityBadge severity={event.severity} />
              </Link>
            </li>
          ))}
          {events?.length === 0 && <li className="text-sm text-gray-400">{t.events.noEvents}</li>}
        </ul>

        <div className="mt-8 max-w-md">
          <PlaceSearch label={t.ux.planStartPlace} onPick={onPlace} />
        </div>

        <button type="button" onClick={onBlank} className="btn-ghost mt-6">
          <MapIcon className="h-4 w-4" aria-hidden="true" />
          {t.ux.planStartBlank}
        </button>
      </div>
    </main>
  );
}
