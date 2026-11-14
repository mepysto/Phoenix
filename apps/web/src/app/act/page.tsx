"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { ArrowRight, HandHeart, LayoutGrid, Plus, Trophy } from "lucide-react";
import { Header } from "@/components/layout/Header";
import { SeverityBadge } from "@/components/event/Badges";
import { EventTypeIcon } from "@/components/event/EventTypeIcon";
import { eventsAPI, type ApiDisasterEvent } from "@/lib/api/client";
import { challengesAPI, communityAPI, plansAPI } from "@/lib/api/community";
import { placeName } from "@/lib/eventPlace";
import { useTranslation } from "@/lib/i18n/useTranslation";
import { severityColor } from "@/lib/severity";
import { approvedOrgs, useAuthStore } from "@/store/authStore";

const LIST_SIZE = 5;

interface Counts {
  needs: number;
  plans: number;
  challenges: number;
}

/**
 * "Take part" (UX plan 5.4): the three ways to help, then the disasters
 * where help is asked for, each leading to its page's "Needs and help" tab.
 */
export default function ActPage() {
  const { t, lang } = useTranslation();
  const me = useAuthStore((s) => s.me);
  const isOrgMember = approvedOrgs(me).length > 0;
  const [counts, setCounts] = useState<Counts | null>(null);
  const [disasters, setDisasters] = useState<{ event: ApiDisasterEvent; needs: number }[] | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const [needs, plans, challenges] = await Promise.all([
        communityAPI.needs({ status: "open", limit: 100 }).catch(() => ({ data: [], total: 0 })),
        plansAPI.list().catch(() => ({ data: [] })),
        challengesAPI.list().catch(() => ({ data: [] })),
      ]);
      if (cancelled) return;
      setCounts({
        needs: needs.total ?? needs.data.length,
        plans: plans.data.length,
        challenges: challenges.data.filter((c) => c.isOpen).length,
      });

      // Disasters with posted needs first, most needs first
      const perEvent = new Map<string, number>();
      for (const need of needs.data) {
        if (need.eventId) perEvent.set(need.eventId, (perEvent.get(need.eventId) ?? 0) + 1);
      }
      const withNeeds = [...perEvent.entries()].sort((a, b) => b[1] - a[1]).slice(0, LIST_SIZE);
      const asked = (
        await Promise.all(
          withNeeds.map(([id, n]) =>
            eventsAPI
              .get(id)
              .then((event) => ({ event: event as ApiDisasterEvent, needs: n }))
              .catch(() => null),
          ),
        )
      ).filter((x): x is { event: ApiDisasterEvent; needs: number } => x !== null);
      // ...then the most severe ongoing disasters
      const severe =
        asked.length < LIST_SIZE
          ? (await eventsAPI.list({ isActive: true }, LIST_SIZE * 2, 0, "importance").catch(() => ({ data: [] }))).data
          : [];
      const seen = new Set(asked.map((a) => a.event.id));
      const rest = severe.filter((e) => !seen.has(e.id)).map((event) => ({ event, needs: 0 }));
      if (!cancelled) setDisasters([...asked, ...rest].slice(0, LIST_SIZE));
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const ways = useMemo(
    () => [
      {
        href: "/connect",
        icon: HandHeart,
        title: t.ux.navNeeds,
        body: t.ux.navNeedsHint,
        count: counts && t.ux.actNeedsCount.replace("{n}", counts.needs.toLocaleString(lang)),
      },
      {
        href: "/plan",
        icon: LayoutGrid,
        title: t.ux.navPlan,
        body: t.ux.navPlanHint,
        count: counts && t.ux.actPlansCount.replace("{n}", counts.plans.toLocaleString(lang)),
      },
      {
        href: "/challenges",
        icon: Trophy,
        title: t.ux.navChallenges,
        body: t.ux.navChallengesHint,
        count: counts && t.ux.actChallengesCount.replace("{n}", counts.challenges.toLocaleString(lang)),
      },
    ],
    [t, lang, counts],
  );

  return (
    <div className="flex min-h-screen flex-col bg-gray-950">
      <Header />
      <main className="flex-1 px-4 py-8 md:px-6 lg:px-8">
        <div className="mx-auto max-w-5xl">
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div>
              <h1 className="text-3xl font-semibold tracking-tight text-white">{t.ux.actTitle}</h1>
              <p className="mt-2 max-w-2xl text-gray-300">{t.ux.actIntro}</p>
            </div>
            {isOrgMember && (
              <Link href="/connect/mine" className="btn-primary">
                <Plus className="h-4 w-4" aria-hidden="true" />
                {t.ux.actPostNeed}
              </Link>
            )}
          </div>

          <ul className="mt-6 grid gap-3 md:grid-cols-3">
            {ways.map(({ href, icon: Icon, title, body, count }) => (
              <li key={href}>
                <Link
                  href={href}
                  className="group flex h-full flex-col rounded-xl border border-gray-700/80 bg-gray-900 p-5 transition-colors hover:border-primary-400/60"
                >
                  <Icon className="h-6 w-6 text-primary-300" aria-hidden="true" />
                  <span className="mt-3 flex items-center gap-2 text-lg font-semibold text-white">
                    {title}
                    <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5 rtl:rotate-180" aria-hidden="true" />
                  </span>
                  <span className="mt-1 text-sm text-gray-300">{body}</span>
                  <span className="mt-auto pt-4 text-sm font-medium tabular-nums text-gray-400">{count ?? " "}</span>
                </Link>
              </li>
            ))}
          </ul>

          <section aria-labelledby="need-help-title" className="mt-10">
            <h2 id="need-help-title" className="text-xl font-semibold text-white">
              {t.ux.actNeedHelpTitle}
            </h2>
            <p className="mt-1 text-sm text-gray-400">{t.ux.actNeedHelpIntro}</p>
            {disasters === null ? (
              <ul className="mt-4 space-y-2" aria-busy="true">
                {Array.from({ length: 3 }, (_, i) => (
                  <li key={i} className="h-16 animate-pulse rounded-xl border border-gray-700/80 bg-gray-900" />
                ))}
              </ul>
            ) : (
              <ul className="mt-4 space-y-2">
                {disasters.map(({ event, needs }) => (
                  <li key={event.id}>
                    <Link
                      href={`/events/${event.id}?tab=help`}
                      className="relative flex items-center gap-4 overflow-hidden rounded-xl border border-gray-700/80 bg-gray-900 py-3 pe-4 ps-5 hover:border-gray-600"
                    >
                      <span
                        aria-hidden="true"
                        className="absolute inset-y-0 start-0 w-1.5"
                        style={{ backgroundColor: severityColor(event.severity) }}
                      />
                      <EventTypeIcon type={event.type} className="h-5 w-5 shrink-0 text-gray-300" />
                      <span className="min-w-0 flex-1">
                        <span className="block font-medium text-white">{event.title}</span>
                        <span className="block text-sm text-gray-400">{placeName(event)}</span>
                      </span>
                      <SeverityBadge severity={event.severity} />
                      {needs > 0 && (
                        <span className="shrink-0 rounded-full bg-primary-400/15 px-2.5 py-0.5 text-sm font-medium text-primary-200">
                          {t.ux.needsN.replace("{n}", String(needs))}
                        </span>
                      )}
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>
      </main>
    </div>
  );
}
