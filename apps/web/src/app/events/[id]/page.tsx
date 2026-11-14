"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { AlertTriangle, ArrowLeft } from "lucide-react";
import { Header } from "@/components/layout/Header";
import { EventDesign, EventNeeds, EventUpdates } from "@/components/event/EventCommunity";
import { EventHeader } from "@/components/event/hub/EventHeader";
import { SituationTab } from "@/components/event/hub/SituationTab";
import { SummaryCells } from "@/components/event/hub/SummaryCells";
import { useEventHub } from "@/hooks/useEventHub";
import { useTranslation } from "@/lib/i18n/useTranslation";

type Tab = "situation" | "help" | "design" | "news";
const TABS: Tab[] = ["situation", "help", "design", "news"];

function initialTab(): Tab {
  if (typeof window === "undefined") return "situation";
  const tab = new URLSearchParams(window.location.search).get("tab");
  return (TABS as string[]).includes(tab ?? "") ? (tab as Tab) : "situation";
}

/**
 * The event page as the hub between seeing and acting (UX plan 5.3): what
 * happened and the ways to help on top, then four tabs.
 */
export default function EventDetailPage() {
  const params = useParams();
  const eventId = params.id as string;
  const { t } = useTranslation();
  const hub = useEventHub(eventId);
  const [tab, setTabState] = useState<Tab>(initialTab);

  const setTab = (next: Tab) => {
    setTabState(next);
    // A link to this page can open on a tab
    const url = new URL(window.location.href);
    if (next === "situation") url.searchParams.delete("tab");
    else url.searchParams.set("tab", next);
    window.history.replaceState(window.history.state, "", `${url.pathname}${url.search}`);
  };

  if (hub.loading && !hub.event) {
    return (
      <div className="flex min-h-screen flex-col bg-gray-950">
        <Header />
        <main role="status" aria-label={t.detail.loading} className="flex-1 px-4 py-6 md:px-6 lg:px-8">
          <div className="mx-auto max-w-6xl space-y-4 pt-4">
            <div className="h-24 animate-pulse rounded-xl border border-gray-700/80 bg-gray-900" />
            <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
              {[0, 1, 2, 3].map((i) => (
                <div key={i} className="h-20 animate-pulse rounded-xl border border-gray-700/80 bg-gray-900" />
              ))}
            </div>
            <div className="h-80 animate-pulse rounded-xl border border-gray-700/80 bg-gray-900" />
          </div>
        </main>
      </div>
    );
  }

  const event = hub.event;
  if (hub.errorStatus !== null || !event) {
    const notFound = hub.errorStatus === null || hub.errorStatus === 404;
    return (
      <div className="flex min-h-screen flex-col bg-gray-950">
        <Header />
        <div className="flex flex-1 items-center justify-center px-4">
          <div className="text-center">
            <AlertTriangle className="mx-auto mb-4 h-12 w-12 text-red-500" aria-hidden="true" />
            <h2 className="mb-2 text-xl font-semibold text-white">{notFound ? t.detail.notFound : t.errors.errorTitle}</h2>
            <p className="mb-4 text-gray-400">{notFound ? t.detail.notFoundBody : t.errors.errorBody}</p>
            <Link href="/events" className="btn-primary">
              <ArrowLeft className="h-4 w-4 rtl:rotate-180" aria-hidden="true" />
              {t.detail.back}
            </Link>
          </div>
        </div>
      </div>
    );
  }

  const count = (n: number | undefined) => (n ? ` (${n})` : "");
  const labels: Record<Tab, string> = {
    situation: t.ux.tabSituation,
    help: `${t.ux.tabHelp}${count(hub.needsTotal)}`,
    design: `${t.ux.tabDesign}${count((hub.plans?.length ?? 0) + (hub.challenges?.length ?? 0))}`,
    news: `${t.ux.tabNews}${count(hub.updates?.length)}`,
  };

  return (
    <div className="flex min-h-screen flex-col bg-gray-950">
      <Header />
      {/* pb: room for the phone action bar */}
      <main className="flex-1 px-4 pb-24 pt-4 md:px-6 lg:px-8 lg:pb-10">
        <div className="mx-auto max-w-6xl">
          <EventHeader event={event} />
          <SummaryCells event={event} needsTotal={hub.needsTotal} />

          <div role="tablist" aria-label={event.title} className="mt-6 flex gap-1 overflow-x-auto border-b border-gray-800">
            {TABS.map((id) => (
              <button
                key={id}
                id={`event-tab-${id}`}
                type="button"
                role="tab"
                aria-selected={tab === id}
                aria-controls={`event-panel-${id}`}
                onClick={() => setTab(id)}
                className={`shrink-0 border-b-2 px-4 py-3 text-sm font-medium transition-colors ${
                  tab === id ? "border-primary-400 text-white" : "border-transparent text-gray-400 hover:text-white"
                }`}
              >
                {labels[id]}
              </button>
            ))}
          </div>

          <div id={`event-panel-${tab}`} role="tabpanel" aria-labelledby={`event-tab-${tab}`} className="mt-5">
            {tab === "situation" && <SituationTab event={event} damage={hub.damage} damageFailed={hub.damageFailed} />}
            {tab === "help" && <EventNeeds eventId={event.id} needs={hub.needs} />}
            {tab === "design" && <EventDesign eventId={event.id} plans={hub.plans} challenges={hub.challenges} />}
            {tab === "news" && <EventUpdates eventId={event.id} updates={hub.updates} onPublished={hub.addUpdate} />}
          </div>
        </div>
      </main>
    </div>
  );
}
