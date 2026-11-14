"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowLeft, Bell, Check, HandHeart, LayoutGrid, Link2 } from "lucide-react";
import { SeverityBadge, TypeBadge } from "@/components/event/Badges";
import type { ApiDisasterEventDetail } from "@/lib/api/client";
import { getEventPosition } from "@/lib/eventPosition";
import { placeName } from "@/lib/eventPlace";
import { formatDate } from "@/lib/format";
import { useTranslation } from "@/lib/i18n/useTranslation";

const DAY_MS = 86_400_000;

/** Which day of the disaster today is (day 1 = the day it began) */
export function dayOfEvent(startDate: string, now = Date.now()): number {
  return Math.max(1, Math.floor((now - Date.parse(startDate)) / DAY_MS) + 1);
}

function useActions(event: ApiDisasterEventDetail) {
  const { t } = useTranslation();
  const [copied, setCopied] = useState(false);
  const position = getEventPosition(event);
  const place = placeName(event);
  const share = async () => {
    try {
      await navigator.clipboard.writeText(window.location.href);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard blocked: the address bar has the link
    }
  };
  return [
    { key: "help", href: `/connect?event=${event.id}`, label: t.connect.offerHelp, icon: HandHeart, primary: true },
    { key: "plan", href: `/plan?event=${event.id}`, label: t.ux.navPlan, icon: LayoutGrid },
    {
      key: "alerts",
      href: position
        ? `/alerts?lat=${position.lat.toFixed(2)}&lng=${position.lng.toFixed(2)}&name=${encodeURIComponent(place)}`
        : "/alerts",
      label: t.alerts.watch,
      icon: Bell,
    },
    { key: "share", onClick: share, label: copied ? t.map.linkCopied : t.ux.shareLink, icon: copied ? Check : Link2 },
  ] as const;
}

/**
 * The top of the event page (UX plan 5.3): what and where, and the ways to
 * act, kept in reach while scrolling (top on wide screens, a bar above the
 * tabs on phones).
 */
export function EventHeader({ event }: { event: ApiDisasterEventDetail }) {
  const { t, lang } = useTranslation();
  const actions = useActions(event);
  const meta = [
    placeName(event),
    t.ux.began.replace("{date}", formatDate(event.startDate, lang)),
    event.isActive ? t.ux.dayN.replace("{n}", String(dayOfEvent(event.startDate))) : null,
  ].filter(Boolean);

  const renderAction = (a: (typeof actions)[number], compact: boolean) => {
    const Icon = a.icon;
    const cls = `${"primary" in a && a.primary ? "btn-primary" : "btn-ghost"} ${compact ? "flex-1 flex-col gap-1 px-1 py-2 text-xs" : ""}`;
    return "href" in a ? (
      <Link key={a.key} href={a.href} className={cls}>
        <Icon className="h-4 w-4" aria-hidden="true" />
        {a.label}
      </Link>
    ) : (
      <button key={a.key} type="button" onClick={a.onClick} className={cls} aria-live="polite">
        <Icon className="h-4 w-4" aria-hidden="true" />
        {a.label}
      </button>
    );
  };

  return (
    <>
      <div className="z-30 -mx-4 bg-gray-950/95 px-4 pb-4 pt-1 backdrop-blur md:-mx-6 md:px-6 lg:sticky lg:top-14 lg:-mx-8 lg:px-8">
        <Link href="/events" className="inline-flex items-center gap-2 text-sm text-gray-400 hover:text-white">
          <ArrowLeft className="h-4 w-4 rtl:rotate-180" aria-hidden="true" />
          {t.detail.back}
        </Link>
        <div className="mt-3 flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <SeverityBadge severity={event.severity} />
              <TypeBadge type={event.type} />
              {event.trust && (
                <span className="text-sm text-gray-300">{t.trust.stages[event.trust.lifecycle]}</span>
              )}
            </div>
            <h1 className="mt-2 text-2xl font-bold leading-tight text-white">{event.title}</h1>
            <p className="mt-1 text-sm text-gray-300">{meta.join(" · ")}</p>
          </div>
          <nav aria-label={t.ux.actions} className="hidden flex-wrap gap-2 lg:flex">
            {actions.map((a) => renderAction(a, false))}
          </nav>
        </div>
      </div>
      {/* Phones: the same actions in a bar above the tab bar */}
      <nav
        aria-label={t.ux.actions}
        className="fixed inset-x-0 bottom-[var(--bottom-nav-h)] z-40 flex gap-1.5 border-t border-gray-800 bg-gray-950/95 px-2 py-2 backdrop-blur lg:hidden"
      >
        {actions.map((a) => renderAction(a, true))}
      </nav>
    </>
  );
}
