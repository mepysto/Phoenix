"use client";

import { useEffect, useMemo, useState } from "react";
import { Check, ClipboardCopy, FileText, Printer } from "lucide-react";
import { viewAPI, type ApiDamageSummary, type ApiDisasterEvent } from "@/lib/api/client";
import { getEventPosition } from "@/lib/eventPosition";
import { useTranslation } from "@/lib/i18n/useTranslation";
import { buildSitrep, sitrepToText, type SitrepNearby } from "@/lib/sitrep";

const NEARBY_KM = 300;

/**
 * Situation report for one event, compiled in the viewer's language from the
 * event and its neighbours. Copy as plain text, or print.
 */
export function SitrepPanel({ event, damage }: { event: ApiDisasterEvent; damage?: ApiDamageSummary | null }) {
  const { t, lang } = useTranslation();
  const [nearby, setNearby] = useState<SitrepNearby[] | null>(null);
  const [copied, setCopied] = useState(false);
  const position = getEventPosition(event);

  useEffect(() => {
    if (!position) {
      setNearby([]);
      return;
    }
    const controller = new AbortController();
    viewAPI
      .nearby(
        position.lat,
        position.lng,
        NEARBY_KM,
        undefined,
        controller.signal,
      )
      .then((res) =>
        setNearby(
          res.data
            .filter((n) => n.event.id !== event.id)
            .map((n) => ({ event: n.event, distanceKm: n.distanceKm })),
        ),
      )
      .catch(() => {
        if (!controller.signal.aborted) setNearby([]);
      });
    return () => controller.abort();
    // position is derived from event; re-run only when the event changes
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [event.id]);

  const report = useMemo(
    () =>
      nearby
        ? buildSitrep(
            event,
            nearby,
            t,
            lang,
            undefined,
            damage
              ? { total: damage.total, destroyed: damage.byGrade.destroyed ?? 0, damaged: damage.byGrade.damaged ?? 0 }
              : null,
          )
        : null,
    [event, nearby, t, lang, damage],
  );

  const copy = async () => {
    if (!report) return;
    try {
      await navigator.clipboard.writeText(sitrepToText(report, t));
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard blocked: the text is still on screen to select by hand
    }
  };

  return (
    <section
      className="sitrep rounded-xl border border-gray-700/80 bg-gray-900"
      aria-labelledby="sitrep-title"
    >
      <header className="flex flex-wrap items-center justify-between gap-2 border-b border-gray-800 px-5 py-4">
        <div className="flex items-center gap-2">
          <FileText className="h-4 w-4 text-primary-400" aria-hidden="true" />
          <h2 id="sitrep-title" className="text-base font-semibold text-white">
            {t.sitrep.title}
          </h2>
        </div>
        <div className="flex items-center gap-1 print:hidden">
          <button
            type="button"
            onClick={copy}
            disabled={!report}
            className="flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs font-medium text-gray-200 hover:bg-gray-800 disabled:text-gray-600"
          >
            {copied ? (
              <Check
                className="h-3.5 w-3.5 text-primary-400"
                aria-hidden="true"
              />
            ) : (
              <ClipboardCopy className="h-3.5 w-3.5" aria-hidden="true" />
            )}
            <span aria-live="polite">
              {copied ? t.sitrep.copied : t.sitrep.copy}
            </span>
          </button>
          <button
            type="button"
            onClick={() => window.print()}
            disabled={!report}
            className="flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs font-medium text-gray-200 hover:bg-gray-800 disabled:text-gray-600"
          >
            <Printer className="h-3.5 w-3.5" aria-hidden="true" />
            {t.sitrep.print}
          </button>
        </div>
      </header>

      {!report ? (
        <div className="space-y-3 p-5" aria-busy="true">
          {[0.9, 0.7, 0.8].map((w, i) => (
            <div
              key={i}
              className="h-3 animate-pulse rounded bg-gray-800"
              style={{ width: `${w * 100}%` }}
            />
          ))}
        </div>
      ) : (
        <div className="grid gap-x-8 gap-y-5 p-5 md:grid-cols-2">
          {report.sections.map((section) => (
            <div
              key={section.id}
              className={section.id === "summary" ? "md:col-span-2" : undefined}
            >
              <h3 className="mb-1.5 text-sm font-semibold text-gray-200">
                {section.heading}
              </h3>
              <ul className="space-y-1 text-sm leading-relaxed text-gray-300">
                {section.lines.map((line, i) => (
                  <li key={i} className="flex gap-2">
                    <span
                      aria-hidden="true"
                      className={`mt-2 h-1 w-1 shrink-0 rounded-full ${
                        section.id === "next" ? "bg-primary-400" : "bg-gray-500"
                      }`}
                    />
                    <span>{line}</span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}
      <p className="border-t border-gray-800 px-5 py-3 text-xs text-gray-400">
        {t.sitrep.disclaimer}
      </p>
    </section>
  );
}
