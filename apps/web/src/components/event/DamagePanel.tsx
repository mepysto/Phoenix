"use client";

import dynamic from "next/dynamic";
import { ExternalLink, ScanSearch } from "lucide-react";
import type { ApiDamageSummary } from "@/lib/api/client";
import {
  DAMAGE_COLORS,
  DAMAGE_GRADES,
  byGrade,
  type DamageGrade,
} from "@/lib/damage";
import { useTranslation } from "@/lib/i18n/useTranslation";

const DamageMap = dynamic(() => import("./DamageMap"), {
  ssr: false,
  loading: () => <div className="h-full w-full animate-pulse bg-gray-950" />,
});

const LIST_LIMIT = 6;

/**
 * Copernicus EMS damage assessment for an event: share of assessed areas by
 * grade, the areas on a map, and links to the source map products.
 */
export function DamagePanel({
  data,
  failed,
}: {
  data: ApiDamageSummary | null;
  failed: boolean;
}) {
  const { t, lang } = useTranslation();
  const d = t.damage;

  // Nothing to say when the request failed: the rest of the page still works
  if (failed) return null;

  return (
    <section
      className="overflow-hidden rounded-xl border border-gray-800 bg-gray-900"
      aria-labelledby="damage-title"
    >
      <header className="flex flex-wrap items-baseline justify-between gap-2 px-5 pb-3 pt-4">
        <h2
          id="damage-title"
          className="flex items-center gap-2 text-base font-semibold text-white"
        >
          <ScanSearch className="h-4 w-4 text-ember-400" aria-hidden="true" />
          {d.title}
        </h2>
        {data && data.total > 0 && (
          <span className="text-xs text-gray-400">
            {d.areas.replace("{n}", data.total.toLocaleString(lang))}
            {data.updatedAt
              ? ` · ${d.updated.replace("{time}", new Date(data.updatedAt).toLocaleDateString(lang, { dateStyle: "medium" }))}`
              : ""}
          </span>
        )}
      </header>

      {data === null ? (
        <div
          className="mx-5 mb-5 h-24 animate-pulse rounded-lg bg-gray-800"
          aria-busy="true"
        />
      ) : data.total === 0 ? (
        <p className="px-5 pb-5 text-sm text-gray-400">{d.none}</p>
      ) : (
        <>
          {/* Share of assessed areas by grade, worst on the left */}
          <div className="px-5">
            <div
              className="flex h-3 overflow-hidden rounded-full bg-gray-800"
              aria-hidden="true"
            >
              {DAMAGE_GRADES.map((g) => {
                const n = byGrade(data.byGrade, g) ?? 0;
                if (n === 0) return null;
                return (
                  <span
                    key={g}
                    className="h-full transition-[flex-grow] duration-700"
                    style={{ flexGrow: n, backgroundColor: DAMAGE_COLORS[g] }}
                  />
                );
              })}
            </div>
            <ul className="mt-3 flex flex-wrap gap-x-4 gap-y-1.5 text-xs">
              {DAMAGE_GRADES.filter(
                (g) => (byGrade(data.byGrade, g) ?? 0) > 0,
              ).map((g) => (
                <li key={g} className="flex items-center gap-1.5 text-gray-300">
                  <span
                    aria-hidden="true"
                    className="h-2.5 w-2.5 rounded-sm"
                    style={{ backgroundColor: DAMAGE_COLORS[g] }}
                  />
                  {d.grades[g]}
                  <span className="font-semibold tabular-nums text-gray-100">
                    {byGrade(data.byGrade, g)}
                  </span>
                  {(byGrade(data.areaKm2ByGrade, g) ?? 0) > 0 && (
                    <span className="text-gray-400">
                      · {byGrade(data.areaKm2ByGrade, g)!.toLocaleString(lang)}{" "}
                      km²
                    </span>
                  )}
                </li>
              ))}
            </ul>
          </div>

          <div className="mt-4 h-64 border-y border-gray-800 md:h-80">
            <DamageMap areas={data.areas} />
          </div>

          <ul className="divide-y divide-gray-800">
            {data.areas.slice(0, LIST_LIMIT).map((a) => (
              <li
                key={a.id}
                className="flex items-center gap-3 px-5 py-2.5 text-sm"
              >
                <span
                  aria-hidden="true"
                  className="h-2.5 w-2.5 shrink-0 rounded-full"
                  style={{
                    backgroundColor: DAMAGE_COLORS[a.grade as DamageGrade],
                  }}
                />
                <span className="min-w-0 flex-1 truncate text-gray-200">
                  {a.name || a.activation}
                </span>
                <span className="shrink-0 text-xs text-gray-400">
                  {d.grades[a.grade as DamageGrade]}
                </span>
                {a.url && (
                  <a
                    href={a.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex shrink-0 items-center gap-1 text-xs font-medium text-primary-300 hover:underline"
                  >
                    {d.product}
                    <ExternalLink className="h-3 w-3" aria-hidden="true" />
                  </a>
                )}
              </li>
            ))}
          </ul>
          <p className="border-t border-gray-800 px-5 py-3 text-xs text-gray-400">
            {d.source} {data.activations.join(", ")}
          </p>
        </>
      )}
    </section>
  );
}
