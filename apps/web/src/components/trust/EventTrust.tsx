"use client";

import { Check } from "lucide-react";
import type { ApiDisasterEvent } from "@/lib/api/client";
import { useTranslation } from "@/lib/i18n/useTranslation";

export type ApiEventTrust = NonNullable<ApiDisasterEvent["trust"]>;
export type LifecycleStage = ApiEventTrust["lifecycle"];

export const LIFECYCLE_STAGES: LifecycleStage[] = [
  "detected",
  "verified",
  "responding",
  "recovering",
  "closed",
];

/** Confidence band: colour and label key */
export function confidenceBand(c: number): "high" | "medium" | "low" {
  if (c >= 0.75) return "high";
  if (c >= 0.5) return "medium";
  return "low";
}

const BAND_COLOR = {
  high: "#34d0ac",
  medium: "#f5b83d",
  low: "#ff8a5b",
} as const;

/**
 * Confidence as a ring gauge: the arc fills with how many independent
 * sources confirm the event. Compact enough for map cards.
 */
export function ConfidenceRing({
  trust,
  size = 44,
}: {
  trust: ApiEventTrust;
  size?: number;
}) {
  const { t } = useTranslation();
  const band = confidenceBand(trust.confidence);
  const pct = Math.round(trust.confidence * 100);
  const stroke = 4;
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const sourceText =
    trust.sourceCount === 1
      ? t.trust.oneSource
      : t.trust.sourceCount.replace("{n}", String(trust.sourceCount));

  return (
    <div className="flex items-center gap-3">
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        role="img"
        aria-label={`${t.trust.confidence} ${pct}%`}
        className="shrink-0 -rotate-90"
      >
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          stroke="#2c3a52"
          strokeWidth={stroke}
          fill="none"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          stroke={BAND_COLOR[band]}
          strokeWidth={stroke}
          fill="none"
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={c * (1 - trust.confidence)}
          className="transition-[stroke-dashoffset] duration-700 ease-out"
        />
        <text
          x="50%"
          y="50%"
          dominantBaseline="central"
          textAnchor="middle"
          className="rotate-90 fill-gray-100 text-[11px] font-semibold"
          style={{ transformOrigin: "center" }}
        >
          {pct}
        </text>
      </svg>
      <div className="min-w-0 text-xs leading-snug">
        <div className="font-medium text-gray-100">{t.trust.bands[band]}</div>
        <div className="text-gray-400">{sourceText}</div>
        {trust.reasons.includes("stale") && (
          <div className="text-ember-400">{t.trust.reasons.stale}</div>
        )}
      </div>
    </div>
  );
}

/**
 * Five-stage lifecycle track. Completed stages are filled, the current one
 * is ringed, and every stage name is in the accessible text.
 */
export function LifecycleTrack({
  stage,
  compact = false,
}: {
  stage: LifecycleStage;
  compact?: boolean;
}) {
  const { t } = useTranslation();
  const current = LIFECYCLE_STAGES.indexOf(stage);

  return (
    <div>
      <ol className="flex items-center" aria-label={t.trust.lifecycle}>
        {LIFECYCLE_STAGES.map((s, i) => {
          const done = i < current;
          const now = i === current;
          return (
            <li key={s} className="flex flex-1 items-center last:flex-none">
              <span
                aria-current={now ? "step" : undefined}
                title={t.trust.stages[s]}
                className={`relative flex h-5 w-5 shrink-0 items-center justify-center rounded-full border text-[10px] ${
                  done
                    ? "border-primary-400 bg-primary-400 text-gray-950"
                    : now
                      ? "border-primary-300 bg-gray-900 text-primary-200"
                      : "border-gray-600 bg-gray-900 text-gray-500"
                }`}
              >
                {done ? (
                  <Check className="h-3 w-3" aria-hidden="true" />
                ) : (
                  <span aria-hidden="true">{i + 1}</span>
                )}
                {now && stage !== "closed" && (
                  <span
                    aria-hidden="true"
                    className="absolute inset-0 animate-ring-pulse rounded-full border border-primary-300"
                  />
                )}
                <span className="sr-only">
                  {t.trust.stages[s]}
                  {now ? ` (${t.trust.current})` : ""}
                </span>
              </span>
              {i < LIFECYCLE_STAGES.length - 1 && (
                <span
                  aria-hidden="true"
                  className={`mx-1 h-px flex-1 ${i < current ? "bg-primary-400" : "bg-gray-700"}`}
                />
              )}
            </li>
          );
        })}
      </ol>
      <div className="mt-1.5 flex items-baseline justify-between gap-2 text-xs">
        <span className="font-medium text-primary-200">
          {t.trust.stages[stage]}
        </span>
        {!compact && (
          <span className="text-right text-gray-400">
            {t.trust.stageHelp[stage]}
          </span>
        )}
      </div>
    </div>
  );
}
