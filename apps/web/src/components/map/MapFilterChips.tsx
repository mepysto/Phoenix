"use client";

import { useSearchParams } from "next/navigation";
import { useState } from "react";
import { X } from "lucide-react";
import { parseEventQuery, type Period } from "@/lib/eventQuery";
import { useTranslation } from "@/lib/i18n/useTranslation";
import { useEventStore } from "@/store/eventStore";

/**
 * A search or period that came with the link (from the disaster list) also
 * filters the map; say so, and let the reader drop it.
 */
export function MapFilterChips() {
  const { t } = useTranslation();
  const params = useSearchParams();
  const [shown, setShown] = useState(() => {
    const { q, period } = parseEventQuery(new URLSearchParams(params.toString()));
    return { q, period };
  });
  const setFilter = useEventStore((s) => s.setFilter);
  const periodLabel: Record<Period, string> = {
    "1": t.events.period1,
    "7": t.events.period7,
    "30": t.events.period30,
  };

  const remove = (key: "q" | "period") => {
    setFilter(key === "q" ? { q: undefined } : { startDate: undefined });
    setShown((s) => ({ ...s, [key]: undefined }));
    const url = new URL(window.location.href);
    url.searchParams.delete(key);
    window.history.replaceState(window.history.state, "", `${url.pathname}${url.search}`);
  };

  const chips = [
    shown.q && { key: "q" as const, label: t.events.searchChip.replace("{q}", shown.q) },
    shown.period && { key: "period" as const, label: periodLabel[shown.period] },
  ].filter(Boolean) as { key: "q" | "period"; label: string }[];
  if (chips.length === 0) return null;

  return (
    <ul aria-label={t.events.mapFilters} className="flex flex-wrap gap-2">
      {chips.map(({ key, label }) => (
        <li key={key} className="hud-panel pointer-events-auto flex items-center gap-1 rounded-full py-1 pe-1 ps-3 text-sm text-gray-100">
          {label}
          <button
            type="button"
            onClick={() => remove(key)}
            aria-label={t.events.removeFilter.replace("{name}", label)}
            className="rounded-full p-1 text-gray-400 hover:bg-gray-800 hover:text-white"
          >
            <X className="h-3.5 w-3.5" aria-hidden="true" />
          </button>
        </li>
      ))}
    </ul>
  );
}
