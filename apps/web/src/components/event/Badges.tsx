"use client";

import { severityColor } from "@/lib/severity";
import type { EventType, SeverityLevel } from "@phoenix/shared/types";
import { useTranslation } from "@/lib/i18n/useTranslation";
import { EventTypeIcon } from "./EventTypeIcon";

/*
 * Event badges share one shape: neutral surface, readable text, and the
 * signal colour on a dot. Colour never carries the meaning alone and text
 * never sits on a mid-tone fill.
 */
const badge =
  "inline-flex items-center gap-1.5 rounded-full border border-gray-700/70 bg-gray-800/60 px-2 py-0.5 text-xs font-medium text-gray-200";

/** Type: its icon (the one on the map marker) and name; colour is kept for severity */
export function TypeBadge({ type }: { type: string }) {
  const { t } = useTranslation();
  return (
    <span className={badge}>
      <EventTypeIcon type={type} className="h-3.5 w-3.5 text-gray-300" />
      {t.sidebar[type as EventType] ?? type}
    </span>
  );
}

const SEVERITY_BARS: Record<SeverityLevel, number> = {
  low: 1,
  medium: 2,
  high: 3,
  critical: 4,
};

/** Severity: a four-step meter plus the word, so it reads without colour */
export function SeverityBadge({ severity }: { severity: string }) {
  const { t } = useTranslation();
  const level = (severity in SEVERITY_BARS ? severity : "low") as SeverityLevel;
  const color = severityColor(level);
  return (
    <span className={badge}>
      <span aria-hidden="true" className="flex items-end gap-px">
        {[1, 2, 3, 4].map((i) => (
          <span
            key={i}
            className="w-[3px] rounded-sm"
            style={{
              height: 3 + i * 2,
              backgroundColor: i <= SEVERITY_BARS[level] ? color : "rgb(var(--gray-600))",
            }}
          />
        ))}
      </span>
      {t.sidebar[level]}
    </span>
  );
}

export function ActiveBadge() {
  const { t } = useTranslation();
  return (
    <span className="inline-flex items-center gap-1.5 px-1 text-xs font-medium text-primary-300">
      <span aria-hidden="true" className="relative flex h-1.5 w-1.5">
        <span className="absolute inset-0 animate-ring-pulse rounded-full bg-primary-400" />
        <span className="relative h-1.5 w-1.5 rounded-full bg-primary-400" />
      </span>
      {t.detail.active}
    </span>
  );
}
