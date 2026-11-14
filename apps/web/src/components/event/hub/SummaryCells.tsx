"use client";

import { useState } from "react";
import { ChevronDown } from "lucide-react";
import { ConfidenceRing, LifecycleTrack } from "@/components/trust/EventTrust";
import type { ApiDisasterEventDetail } from "@/lib/api/client";
import { compactNumber } from "@/lib/format";
import { useTranslation } from "@/lib/i18n/useTranslation";

function Cell({ label, value, pending }: { label: string; value: string; pending?: boolean }) {
  return (
    <div className="rounded-xl border border-gray-700/80 bg-gray-900 px-4 py-3">
      <p className="text-sm text-gray-400">{label}</p>
      <p className={pending ? "mt-1 text-base font-medium text-gray-300" : "mt-0.5 text-2xl font-semibold text-white"}>
        {value}
      </p>
    </div>
  );
}

/**
 * Four figures under the title (UX plan 5.3). A missing figure reads "not
 * yet counted", never 0. Confidence opens its explanation.
 */
export function SummaryCells({ event, needsTotal }: { event: ApiDisasterEventDetail; needsTotal: number }) {
  const { t, lang } = useTranslation();
  const [trustOpen, setTrustOpen] = useState(false);
  const notCounted = t.dashboard.notCounted;
  const people = event.affectedPopulation && event.affectedPopulation > 0 ? event.affectedPopulation : null;
  const area = event.affectedAreaKm2 && event.affectedAreaKm2 > 0 ? event.affectedAreaKm2 : null;

  return (
    <div>
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Cell
          label={t.detail.affectedPopulation}
          value={people !== null ? compactNumber(people, lang) : notCounted}
          pending={people === null}
        />
        <Cell
          label={t.ux.cellArea}
          value={area !== null ? `${compactNumber(area, lang)} km²` : notCounted}
          pending={area === null}
        />
        <Cell label={t.ux.cellNeeds} value={needsTotal.toLocaleString(lang)} />
        {event.trust ? (
          <button
            type="button"
            onClick={() => setTrustOpen((o) => !o)}
            aria-expanded={trustOpen}
            aria-controls="trust-detail"
            className="rounded-xl border border-gray-700/80 bg-gray-900 px-4 py-3 text-start hover:border-gray-600"
          >
            <span className="flex items-center justify-between text-sm text-gray-400">
              {t.trust.title}
              <ChevronDown className={`h-4 w-4 transition-transform ${trustOpen ? "rotate-180" : ""}`} aria-hidden="true" />
            </span>{" "}
            <span className="mt-0.5 block text-2xl font-semibold text-white">
              {(event.trust.sourceCount === 1 ? t.ux.confidenceValueOne : t.ux.confidenceValue)
                .replace("{p}", String(Math.round(event.trust.confidence * 100)))
                .replace("{n}", String(event.trust.sourceCount))}
            </span>
          </button>
        ) : (
          <Cell label={t.trust.title} value={notCounted} pending />
        )}
      </div>
      {trustOpen && event.trust && (
        <section id="trust-detail" aria-label={t.trust.title} className="mt-3 rounded-xl border border-gray-700/80 bg-gray-900 p-5">
          <ConfidenceRing trust={event.trust} size={56} />
          <div className="mt-5">
            <LifecycleTrack stage={event.trust.lifecycle} />
          </div>
        </section>
      )}
    </div>
  );
}
