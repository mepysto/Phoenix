"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { BarChart3, RefreshCw } from "lucide-react";
import { Header } from "@/components/layout/Header";
import { EmptyState } from "@/components/ui/States";
import { SeverityBadge, TypeBadge } from "@/components/event/Badges";
import {
  ChartCard,
  ColumnChart,
  RankedBars,
  SegmentedBar,
  StatTile,
  compact,
  full,
} from "@/components/dashboard/Charts";
import { statsAPI, type OverviewStats } from "@/lib/api/community";
import { formatDate, formatRelative } from "@/lib/format";
import { useTranslation } from "@/lib/i18n/useTranslation";
import { severityColor } from "@/lib/severity";
import type { EventType, SeverityLevel } from "@phoenix/shared/types";

const TOP_TYPES = 7;

export default function DashboardPage() {
  const { t, lang } = useTranslation();
  const d = t.dashboard;
  const [stats, setStats] = useState<OverviewStats | null>(null);
  const [failed, setFailed] = useState(false);
  const [metric, setMetric] = useState<"events" | "affected">("events");

  const load = () => {
    setFailed(false);
    statsAPI
      .overview()
      .then(setStats)
      .catch(() => setFailed(true));
  };
  useEffect(load, []);

  const typeLabel = (type: string) => t.sidebar[type as EventType] ?? type;
  const n = (v: number) => d.events.replace("{n}", full(v, lang));

  let body: React.ReactNode;
  if (failed && !stats) {
    body = (
      <EmptyState
        icon={RefreshCw}
        title={d.loadFailed}
        action={
          <button type="button" className="btn-ghost" onClick={load}>
            {t.common.retry}
          </button>
        }
      />
    );
  } else if (!stats) {
    body = (
      <div role="status" aria-label={t.common.loading} className="space-y-4">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          {Array.from({ length: 5 }, (_, i) => (
            <div
              key={i}
              className="h-24 animate-pulse rounded-xl border border-gray-800 bg-gray-900"
            />
          ))}
        </div>
        <div className="grid gap-4 lg:grid-cols-2">
          <div className="h-72 animate-pulse rounded-xl border border-gray-800 bg-gray-900" />
          <div className="h-72 animate-pulse rounded-xl border border-gray-800 bg-gray-900" />
        </div>
      </div>
    );
  } else if (
    stats.activeEvents === 0 &&
    stats.weeklyOnsets.every((w) => w.events === 0)
  ) {
    body = <EmptyState icon={BarChart3} title={d.noData} body={d.noDataBody} />;
  } else {
    const s = stats;
    const weeks = s.weeklyOnsets.map((w) => ({
      key: w.weekStart,
      label: formatDate(w.weekStart, lang),
      value: w.events,
    }));
    const sevTotal = s.bySeverity.reduce((a, b) => a + b.events, 0);
    const sev = s.bySeverity.map((x) => ({
      key: x.severity,
      label: t.sidebar[x.severity as SeverityLevel] ?? x.severity,
      value: x.events,
      color: severityColor(x.severity),
      darkInk: x.severity === "medium",
    }));

    const ranked = [...s.byType].sort((a, b) =>
      metric === "events" ? b.events - a.events : b.affected - a.affected,
    );
    const head = ranked.slice(0, TOP_TYPES);
    const tail = ranked.slice(TOP_TYPES);
    const types = head.map((x) => ({
      key: x.type,
      label: typeLabel(x.type),
      value: metric === "events" ? x.events : x.affected,
      detail: `${typeLabel(x.type)} · ${n(x.events)} · ${compact(x.affected, lang)} ${d.people.toLowerCase()}`,
    }));
    if (tail.length) {
      types.push({
        key: "other",
        label: d.other,
        value: tail.reduce(
          (a, x) => a + (metric === "events" ? x.events : x.affected),
          0,
        ),
        detail: tail.map((x) => typeLabel(x.type)).join(", "),
      });
    }
    const delta = s.newThisWeek - s.newWeekBefore;
    // No estimate is not zero people (UX plan D-01): say so, and give the
    // headline spot to a figure we do have
    const hasAffected = s.affectedEstimated > 0;
    const hasCountries = s.countriesActive > 0;

    body = (
      <div className="space-y-4">
        {/* Hero figure and headline tiles */}
        <div className="grid gap-3 lg:grid-cols-[1.4fr_repeat(4,1fr)]">
          <div className="rounded-xl border border-gray-800 bg-gray-900 px-5 py-4 sm:col-span-2 lg:col-span-1">
            {hasAffected ? (
              <>
                <p className="text-xs font-medium text-gray-400">{d.affected}</p>
                <p className="mt-1 text-5xl font-semibold tracking-tight text-white">
                  {compact(s.affectedActive, lang)}
                </p>
                <p className="mt-1 text-xs text-gray-400">
                  {d.affectedBasis.replace("{n}", full(s.affectedEstimated, lang))}.{" "}
                  {d.affectedNote}
                </p>
              </>
            ) : (
              <>
                <p className="text-xs font-medium text-gray-400">{d.active}</p>
                <p className="mt-1 text-5xl font-semibold tracking-tight text-white">
                  {full(s.activeEvents, lang)}
                </p>
              </>
            )}
          </div>
          <div className="grid grid-cols-2 gap-3 sm:col-span-2 lg:col-span-4 lg:grid-cols-4">
            {hasAffected ? (
              <StatTile label={d.active} value={full(s.activeEvents, lang)} />
            ) : (
              <StatTile
                label={d.affected}
                value={d.notCounted}
                note={d.affectedPending}
                pending
              />
            )}
            <StatTile label={d.critical} value={full(s.criticalActive, lang)} />
            <StatTile
              label={d.countries}
              value={hasCountries ? full(s.countriesActive, lang) : d.notCounted}
              pending={!hasCountries}
            />
            <StatTile
              label={d.newWeek}
              value={full(s.newThisWeek, lang)}
              note={`${delta > 0 ? "▲" : delta < 0 ? "▼" : "•"} ${full(Math.abs(delta), lang)} · ${d.vsPrev.replace("{n}", full(s.newWeekBefore, lang))}`}
              noteTone={
                delta > 0 ? "up-bad" : delta < 0 ? "down-good" : "muted"
              }
            />
          </div>
        </div>

        <div className="grid gap-4 lg:grid-cols-2">
          <ChartCard
            title={d.weekly}
            subtitle={d.weeklySub}
            table={{
              head: [d.week, d.count],
              rows: weeks.map((w) => [w.label, w.value]),
            }}
          >
            <ColumnChart
              data={weeks}
              label={(w) => d.weekOf.replace("{date}", w.label)}
              valueLabel={n}
            />
          </ChartCard>

          <ChartCard
            title={d.severity}
            subtitle={d.severitySub}
            table={{
              head: [t.sidebar.severity, d.count, d.share],
              rows: sev.map((x) => [
                x.label,
                full(x.value, lang),
                `${sevTotal ? Math.round((x.value / sevTotal) * 100) : 0}%`,
              ]),
            }}
          >
            <SegmentedBar data={sev} total={sevTotal} />
          </ChartCard>

          <ChartCard
            title={d.byType}
            table={{
              head: [t.sidebar.eventTypes, d.byTypeEvents, d.byTypePeople],
              rows: ranked.map((x) => [
                typeLabel(x.type),
                full(x.events, lang),
                full(x.affected, lang),
              ]),
            }}
          >
            {hasAffected && (
              <div
                role="group"
                aria-label={d.byType}
                className="mb-4 inline-flex rounded-lg border border-gray-700 p-0.5 text-xs"
              >
                {(["events", "affected"] as const).map((m) => (
                  <button
                    key={m}
                    type="button"
                    aria-pressed={metric === m}
                    onClick={() => setMetric(m)}
                    className={`rounded-md px-3 py-1 font-medium ${
                      metric === m
                        ? "bg-gray-800 text-white"
                        : "text-gray-400 hover:text-white"
                    }`}
                  >
                    {m === "events" ? d.byTypeEvents : d.byTypePeople}
                  </button>
                ))}
              </div>
            )}
            <RankedBars
              data={types}
              format={(v) =>
                metric === "events" ? full(v, lang) : compact(v, lang)
              }
            />
          </ChartCard>

          <ChartCard
            title={d.mostAffected}
            table={{
              head: [d.event, d.people],
              rows: s.topAffected.map((e) => [e.title, full(e.affected, lang)]),
            }}
          >
            {s.topAffected.length === 0 && (
              <p className="text-sm text-gray-400">{d.noChartData}</p>
            )}
            <ol className="space-y-1">
              {s.topAffected.map((e) => (
                <li key={e.id}>
                  <Link
                    href={`/events/${e.id}`}
                    className="flex items-center gap-3 rounded-lg px-2 py-2 hover:bg-gray-800/60"
                  >
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-sm font-medium text-gray-100">
                        {e.title}
                      </span>
                      <span className="mt-1 flex flex-wrap gap-1.5">
                        <TypeBadge type={e.type} />
                        <SeverityBadge severity={e.severity} />
                      </span>
                    </span>
                    <span className="shrink-0 text-end text-sm font-semibold tabular-nums text-white">
                      {compact(e.affected, lang)}
                    </span>
                  </Link>
                </li>
              ))}
            </ol>
            <Link
              href="/events"
              className="mt-3 inline-block text-xs font-medium text-primary-300 hover:underline"
            >
              {d.viewAll}
            </Link>
          </ChartCard>
        </div>

        <section aria-labelledby="community-title" className="space-y-3 pt-2">
          <h2 id="community-title" className="text-lg font-semibold text-white">
            {d.community}
          </h2>
          <div className="grid gap-4 lg:grid-cols-[1fr_2fr]">
            <div className="grid grid-cols-3 gap-3 lg:grid-cols-1">
              <StatTile label={d.needsOpen} value={full(s.needsOpen, lang)} />
              <StatTile label={d.offersOpen} value={full(s.offersOpen, lang)} />
              <StatTile
                label={d.connections}
                value={full(s.connectionsMade, lang)}
              />
            </div>
            <ChartCard
              title={d.needsByCategory}
              table={{
                head: [t.connect.form.categories, d.count],
                rows: s.needsByCategory.map((c) => [
                  t.connect.categories[
                    c.category as keyof typeof t.connect.categories
                  ] ?? c.category,
                  c.open,
                ]),
              }}
            >
              {s.needsByCategory.some((c) => c.open > 0) ? (
                <RankedBars
                  color="bg-ember-400 [html.light_&]:bg-ember-600"
                  data={s.needsByCategory
                    .filter((c) => c.open > 0)
                    .map((c) => ({
                      key: c.category,
                      label:
                        t.connect.categories[
                          c.category as keyof typeof t.connect.categories
                        ] ?? c.category,
                      value: c.open,
                    }))}
                  format={(v) => full(v, lang)}
                />
              ) : (
                <p className="text-sm text-gray-400">{t.connect.noNeeds}</p>
              )}
            </ChartCard>
          </div>
        </section>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col bg-gray-950">
      <Header />
      <main className="flex-1 px-4 py-6 md:px-6 lg:px-8">
        <div className="mx-auto max-w-6xl">
          <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
            <div className="max-w-2xl">
              <h1 className="text-2xl font-bold text-white">{d.title}</h1>
              <p className="mt-1 text-sm text-gray-400">{d.intro}</p>
            </div>
            {stats && (
              <p className="text-xs text-gray-500">
                <time dateTime={stats.generatedAt}>
                  {d.updated.replace(
                    "{time}",
                    formatRelative(stats.generatedAt, lang),
                  )}
                </time>
              </p>
            )}
          </div>
          {body}
        </div>
      </main>
    </div>
  );
}
