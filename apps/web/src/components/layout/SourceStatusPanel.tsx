"use client";

import { useEffect, useState } from "react";
import { Radio } from "lucide-react";
import { sourcesAPI, type ApiSourceStatus } from "@/lib/api/client";
import { useTranslation } from "@/lib/i18n/useTranslation";
import { FilterSection } from "./FilterSection";

const POLL_MS = 60_000;

const STATUS_DOT: Record<ApiSourceStatus["status"], string> = {
  fresh: "bg-green-500",
  stale: "bg-amber-500",
  failing: "bg-red-500",
  never: "bg-gray-500",
};

/** "3 min ago" in the UI language; null for sources that never synced. */
export function formatAge(iso: string | null | undefined, lang: string, now = Date.now()): string | null {
  if (!iso) return null;
  const seconds = Math.round((Date.parse(iso) - now) / 1000);
  const rtf = new Intl.RelativeTimeFormat(lang, { numeric: "auto", style: "short" });
  const abs = Math.abs(seconds);
  if (abs < 60) return rtf.format(seconds, "second");
  if (abs < 3600) return rtf.format(Math.round(seconds / 60), "minute");
  if (abs < 86400) return rtf.format(Math.round(seconds / 3600), "hour");
  return rtf.format(Math.round(seconds / 86400), "day");
}

/**
 * Freshness of each data source, so users can tell "no events" apart from
 * "the feed stopped updating".
 */
export function SourceStatusPanel() {
  const { t, lang } = useTranslation();
  const [sources, setSources] = useState<ApiSourceStatus[] | null>(null);

  useEffect(() => {
    let cancelled = false;
    const load = () =>
      sourcesAPI
        .list()
        .then((data) => !cancelled && setSources(data))
        .catch(() => {
          // Keep the last known status; the map shows API errors separately
        });
    void load();
    const timer = setInterval(load, POLL_MS);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, []);

  if (!sources?.length) return null;

  return (
    <FilterSection title={t.sources.title} icon={<Radio className="h-4 w-4" />}>
      <ul className="space-y-1.5">
        {sources.map((source) => {
          const label = t.sources[source.status];
          return (
            <li
              key={source.name}
              className="flex items-center justify-between gap-2 px-2 text-sm"
              aria-label={t.sources.summary
                .replace("{name}", source.name)
                .replace("{status}", label)}
            >
              <span className="flex items-center gap-2 text-gray-300">
                <span
                  aria-hidden="true"
                  className={`h-2 w-2 shrink-0 rounded-full ${STATUS_DOT[source.status]}`}
                />
                {source.name}
              </span>
              <span
                className={`text-xs ${source.status === "fresh" ? "text-gray-500" : "text-amber-400"}`}
                title={source.lastError ?? undefined}
              >
                {source.status === "fresh"
                  ? formatAge(source.lastSync, lang)
                  : label}
              </span>
            </li>
          );
        })}
      </ul>
    </FilterSection>
  );
}
