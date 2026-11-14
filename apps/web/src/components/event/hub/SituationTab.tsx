"use client";

import { useState } from "react";
import dynamic from "next/dynamic";
import { Globe } from "lucide-react";
import { DamagePanel } from "@/components/event/DamagePanel";
import { SitrepPanel } from "@/components/event/SitrepPanel";
import type { ApiDamageSummary, ApiDisasterEventDetail } from "@/lib/api/client";
import { compareReady } from "@/lib/compare";
import { getEventPosition } from "@/lib/eventPosition";
import { useTranslation } from "@/lib/i18n/useTranslation";

const BeforeAfterCompare = dynamic(
  () => import("@/components/event/BeforeAfterCompare").then((m) => m.BeforeAfterCompare),
  { ssr: false, loading: () => <div className="h-96 animate-pulse rounded-xl bg-gray-900" /> },
);
const MiniMap = dynamic(() => import("@/components/map/MiniMap"), {
  ssr: false,
  loading: () => <div className="h-full w-full animate-pulse bg-gray-800" />,
});

/**
 * The "Situation" tab (UX plan 5.3). Sections with nothing to show do not
 * get a card: they are listed once, at the end, under "Not available yet".
 */
export function SituationTab({
  event,
  damage,
  damageFailed,
}: {
  event: ApiDisasterEventDetail;
  damage: ApiDamageSummary | null;
  damageFailed: boolean;
}) {
  const { t } = useTranslation();
  const position = getEventPosition(event);
  const [forceCompare, setForceCompare] = useState(false);
  const hasDamage = !!damage && damage.total > 0;
  const showCompare = !!position && (forceCompare || compareReady(new Date(event.startDate)));

  const missing: { key: string; text: string; action?: React.ReactNode }[] = [];
  if (!hasDamage && !damageFailed) missing.push({ key: "damage", text: t.ux.missingDamage });
  if (position && !showCompare) {
    missing.push({
      key: "compare",
      text: t.ux.missingCompare,
      action: (
        <button type="button" onClick={() => setForceCompare(true)} className="text-sm font-medium text-primary-300 hover:underline">
          {t.ux.pickDates}
        </button>
      ),
    });
  }

  return (
    <div className="space-y-4">
      <div className="h-64 overflow-hidden rounded-xl border border-gray-700/80 bg-gray-900 lg:h-80">
        {position ? (
          <MiniMap lat={position.lat} lng={position.lng} />
        ) : (
          <div className="flex h-full items-center justify-center text-sm text-gray-400">
            {t.detail.locationUnavailable}
          </div>
        )}
      </div>

      <SitrepPanel event={event} damage={damage} />

      {hasDamage && <DamagePanel data={damage} failed={damageFailed} />}

      {showCompare && position && (
        <BeforeAfterCompare lat={position.lat} lng={position.lng} type={event.type} startDate={event.startDate} />
      )}

      {event.sources && event.sources.length > 0 && (
        <section aria-labelledby="sources-title" className="rounded-xl border border-gray-700/80 bg-gray-900 p-5">
          <h2 id="sources-title" className="mb-3 text-base font-semibold text-white">
            {t.detail.dataSources}
          </h2>
          <ul className="flex flex-wrap gap-2">
            {event.sources.map((source) => (
              <li key={source.id} className="flex items-center gap-2 rounded-lg bg-gray-800/60 px-3 py-2 text-sm text-gray-200">
                <Globe className="h-4 w-4 text-gray-400" aria-hidden="true" />
                {source.name}
              </li>
            ))}
          </ul>
        </section>
      )}

      {missing.length > 0 && (
        <section aria-labelledby="not-yet-title" className="rounded-xl border border-dashed border-gray-700 px-5 py-4">
          <h2 id="not-yet-title" className="text-sm font-semibold text-gray-200">
            {t.ux.notYetTitle}
          </h2>
          <ul className="mt-2 space-y-1.5">
            {missing.map((m) => (
              <li key={m.key} className="flex flex-wrap items-baseline gap-x-3 text-sm text-gray-400">
                <span>{m.text}</span>
                {m.action}
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
