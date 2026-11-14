"use client";

import { Suspense, useCallback, useMemo } from "react";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { AlertTriangle, Map as MapIcon, RefreshCw } from "lucide-react";
import { Header } from "@/components/layout/Header";
import { EventFilters } from "@/components/events/EventFilters";
import { EventRow } from "@/components/events/EventRow";
import { EmptyState } from "@/components/ui/States";
import { useEventList } from "@/hooks/useEventList";
import {
  parseEventQuery,
  serializeEventQuery,
  sharedFilterQuery,
  type EventQuery,
} from "@/lib/eventQuery";
import { useTranslation } from "@/lib/i18n/useTranslation";

/**
 * The disaster list (UX plan 5.2): most important first, one per line, with
 * filters that live in the URL and travel to and from the map.
 */
function EventsPageContent() {
  const { t, lang } = useTranslation();
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const search = params.toString();
  const query = useMemo(() => parseEventQuery(new URLSearchParams(search)), [search]);
  const list = useEventList(query);

  const update = useCallback(
    (patch: Partial<EventQuery>) => {
      const qs = serializeEventQuery({ ...query, ...patch }, new URLSearchParams(search));
      router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
    },
    [query, search, pathname, router],
  );

  const shared = sharedFilterQuery(search);
  const number = (n: number) => n.toLocaleString(lang);

  let body: React.ReactNode;
  if (list.error && list.events.length === 0) {
    body = (
      <EmptyState
        icon={RefreshCw}
        title={t.events.noEvents}
        action={
          <button type="button" className="btn-ghost" onClick={list.reload}>
            {t.common.retry}
          </button>
        }
      />
    );
  } else if (list.loading && list.events.length === 0) {
    body = (
      <ul role="status" aria-label={t.common.loading} className="space-y-2">
        {Array.from({ length: 8 }, (_, i) => (
          <li key={i} className="h-16 animate-pulse rounded-xl border border-gray-700/80 bg-gray-900" />
        ))}
      </ul>
    );
  } else if (list.events.length === 0) {
    body = (
      <EmptyState
        icon={AlertTriangle}
        title={t.events.noEvents}
        body={t.events.adjustFilters}
        action={
          <button
            type="button"
            className="btn-ghost"
            onClick={() => update({ types: undefined, severities: undefined, q: undefined, period: undefined })}
          >
            {t.events.clearFilters}
          </button>
        }
      />
    );
  } else {
    body = (
      <>
        <ul className={`space-y-2 transition-opacity ${list.loading ? "opacity-60" : ""}`}>
          {list.events.map((event) => (
            <EventRow key={event.id} event={event} />
          ))}
        </ul>
        {list.hasMore && (
          <div className="mt-4 flex justify-center">
            <button type="button" className="btn-ghost" onClick={list.loadMore} disabled={list.loadingMore}>
              {t.events.loadMore}
            </button>
          </div>
        )}
      </>
    );
  }

  return (
    <div className="flex min-h-screen flex-col bg-gray-950">
      <Header />

      <main className="flex-1 px-4 py-6 md:px-6 lg:px-8">
        <div className="mx-auto max-w-6xl">
          <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
            <div>
              <h1 className="text-2xl font-bold text-white">{t.events.title}</h1>
              <p className="mt-1 text-sm text-gray-400" aria-live="polite">
                {list.loading && list.events.length === 0
                  ? t.common.loading
                  : t.events.showing
                      .replace("{shown}", number(list.events.length))
                      .replace("{total}", number(list.total))}
              </p>
            </div>
            <Link href={shared ? `/?${shared}` : "/"} className="btn-primary">
              <MapIcon className="h-4 w-4" aria-hidden="true" />
              {t.common.viewOnMap}
            </Link>
          </div>

          <div className="mb-5">
            <EventFilters query={query} facets={list.facets} onChange={update} />
          </div>

          {body}
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
