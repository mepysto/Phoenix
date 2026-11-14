"use client";

import dynamic from "next/dynamic";
import { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import {
  Check,
  Cross,
  Droplet,
  Eraser,
  Link2,
  Package,
  Sparkles,
  Tent,
  Toilet,
  Trash2,
  TriangleAlert,
  X,
  type LucideIcon,
} from "lucide-react";
import { Header } from "@/components/layout/Header";
import { KIND_COLORS } from "@/components/plan/kindColors";
import { PlanSaveBar } from "@/components/plan/PlanSaveBar";
import { plansAPI, type PlanOut } from "@/lib/api/community";
import { eventsAPI } from "@/lib/api/client";
import { getEventPosition } from "@/lib/eventPosition";
import { useTranslation } from "@/lib/i18n/useTranslation";
import {
  autoLayout,
  decodePlan,
  encodePlan,
  evaluate,
  fromWire,
  newId,
  waterLitresPerDay,
  type ItemKind,
  type Kpi,
  type PlanItem,
} from "@/lib/sphere";

const PlanMap = dynamic(() => import("@/components/plan/PlanMap"), {
  ssr: false,
  loading: () => <div className="h-full w-full animate-pulse bg-gray-900" />,
});

type Tool = ItemKind | "remove";

const TOOLS: { id: Tool; icon: LucideIcon; key: string }[] = [
  { id: "tent", icon: Tent, key: "1" },
  { id: "tap", icon: Droplet, key: "2" },
  { id: "toilet", icon: Toilet, key: "3" },
  { id: "health", icon: Cross, key: "4" },
  { id: "distribution", icon: Package, key: "5" },
  { id: "remove", icon: Eraser, key: "0" },
];

const STATUS_STYLE = {
  ok: { text: "text-primary-300", bar: "bg-primary-400", Icon: Check },
  warn: { text: "text-amber-300", bar: "bg-amber-400", Icon: TriangleAlert },
  fail: { text: "text-ember-400", bar: "bg-ember-500", Icon: X },
} as const;

function KpiRow({ kpi, lang }: { kpi: Kpi; lang: string }) {
  const { t } = useTranslation();
  const s = STATUS_STYLE[kpi.status];
  const unit =
    kpi.id === "space" || kpi.id === "siteArea"
      ? " m²"
      : kpi.id === "waterDistance" || kpi.id === "toiletDistance"
        ? "%"
        : "";
  return (
    <li className="py-3">
      <div className="flex items-baseline justify-between gap-3">
        <span className="text-sm text-gray-200">{t.plan.kpis[kpi.id]}</span>
        <span
          className={`flex items-center gap-1 text-sm font-semibold tabular-nums ${s.text}`}
        >
          <s.Icon className="h-3.5 w-3.5" aria-hidden="true" />
          <span className="sr-only">{t.plan.status[kpi.status]}:</span>
          {kpi.value.toLocaleString(lang)}
          {unit}
        </span>
      </div>
      <div
        className="mt-1.5 h-1 overflow-hidden rounded-full bg-gray-800"
        aria-hidden="true"
      >
        <div
          className={`h-full rounded-full transition-[width] duration-500 ${s.bar}`}
          style={{ width: `${kpi.progress * 100}%` }}
        />
      </div>
      <p className="mt-1 text-xs text-gray-400">
        {t.plan.target.replace(
          "{target}",
          `${kpi.id === "toilets" ? "≤ " : ""}${kpi.target.toLocaleString(lang)}${unit}`,
        )}
      </p>
    </li>
  );
}

function Planner() {
  const { t, lang } = useTranslation();
  const params = useSearchParams();
  const planId = params.get("id");
  const [plan, setPlan] = useState<PlanOut | null>(null);
  const eventId = params.get("event") ?? plan?.eventId ?? null;
  const [center, setCenter] = useState({ lat: 24.89, lng: 91.87 });
  const [eventTitle, setEventTitle] = useState<string | null>(null);
  const [population, setPopulation] = useState(1000);
  const [items, setItems] = useState<PlanItem[]>([]);
  const [tool, setTool] = useState<Tool>("tent");
  const [showReach, setShowReach] = useState(true);
  const [fitSignal, setFitSignal] = useState(0);
  const [copied, setCopied] = useState(false);

  /** Show a saved plan's version; keep its id in the address */
  const applyPlan = useCallback((next: PlanOut, fit: boolean) => {
    setPlan(next);
    setPopulation(next.population);
    const loaded = fromWire(next.items as [number, number, number][]);
    setItems(loaded);
    const first = loaded[0];
    if (fit && first) {
      setCenter({ lat: first.lat, lng: first.lng });
      setFitSignal((n) => n + 1);
    }
    const v =
      next.version !== next.latestVersion ? `&version=${next.version}` : "";
    window.history.replaceState(null, "", `/plan?id=${next.id}${v}`);
  }, []);

  useEffect(() => {
    if (!planId) return;
    const version = Number(params.get("version")) || undefined;
    plansAPI
      .get(planId, version)
      .then((p) => applyPlan(p, true))
      .catch(() => {});
    // Load once per plan id
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [planId]);

  // A shared plan in the URL hash wins; otherwise centre on the event
  useEffect(() => {
    if (planId) return;
    const hash =
      typeof window !== "undefined"
        ? window.location.hash.match(/plan=([\w-]+)/)
        : null;
    const shared = hash ? decodePlan(hash[1]!) : null;
    if (shared) {
      setPopulation(shared.population);
      setItems(shared.items);
      const first = shared.items[0];
      if (first) setCenter({ lat: first.lat, lng: first.lng });
      setFitSignal((n) => n + 1);
    }
    if (!eventId) return;
    eventsAPI
      .get(eventId)
      .then((e) => {
        setEventTitle(e.title);
        // A saved plan keeps its own site and population
        if (planId) return;
        const p = getEventPosition(e);
        if (p && !shared) setCenter(p);
        if (!shared && e.affectedPopulation && e.affectedPopulation > 0) {
          // Plan for a camp-sized share of the affected people
          setPopulation(
            Math.min(
              20_000,
              Math.max(100, Math.round(e.affectedPopulation / 10 / 100) * 100),
            ),
          );
        }
      })
      .catch(() => {});
    // planId only changes with navigation, which remounts the page
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [eventId]);

  // Keep the share link current without adding history entries (unsaved plans)
  useEffect(() => {
    if (items.length === 0 || plan) return;
    const url = `${window.location.pathname}${window.location.search}#plan=${encodePlan({ population, items })}`;
    window.history.replaceState(null, "", url);
  }, [items, population, plan]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      if (target.closest("input, textarea, select")) return;
      const hit = TOOLS.find((x) => x.key === e.key);
      if (hit) setTool(hit.id);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const kpis = useMemo(
    () => evaluate({ population, items }),
    [population, items],
  );
  const met = kpis.filter((k) => k.status === "ok").length;

  const onMapClick = useCallback(
    (lat: number, lng: number) => {
      if (tool === "remove") return;
      setItems((list) => [...list, { id: newId(), kind: tool, lat, lng }]);
    },
    [tool],
  );
  const onItemClick = useCallback(
    (id: string) => {
      if (tool === "remove")
        setItems((list) => list.filter((i) => i.id !== id));
    },
    [tool],
  );

  const share = async () => {
    try {
      await navigator.clipboard.writeText(window.location.href);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      // The link is in the address bar
    }
  };

  return (
    <main className="flex flex-1 flex-col lg:min-h-0 lg:flex-row">
      <div className="relative h-[62vh] min-h-[340px] shrink-0 lg:h-auto lg:flex-1">
        <PlanMap
          center={center}
          items={items}
          showReach={showReach}
          onMapClick={onMapClick}
          onItemClick={onItemClick}
          cursor={tool === "remove" ? "not-allowed" : "crosshair"}
          fitSignal={fitSignal}
        />
        <div
          role="toolbar"
          aria-label={t.plan.tools}
          className="hud-panel absolute start-3 top-3 flex gap-1 rounded-xl p-1.5 lg:flex-col"
        >
          {TOOLS.map(({ id, icon: Icon, key }) => {
            const label = id === "remove" ? t.plan.remove : t.plan.kinds[id];
            return (
              <button
                key={id}
                type="button"
                aria-pressed={tool === id}
                aria-keyshortcuts={key}
                title={`${label} (${key})`}
                onClick={() => setTool(id)}
                className={`flex h-10 min-w-10 items-center justify-center gap-2 rounded-lg transition-colors lg:justify-start lg:px-2.5 ${
                  tool === id
                    ? "bg-gray-700 text-white"
                    : "text-gray-300 hover:bg-gray-800"
                }`}
              >
                <Icon
                  className="h-5 w-5 shrink-0"
                  style={
                    id !== "remove" ? { color: KIND_COLORS[id] } : undefined
                  }
                  aria-hidden="true"
                />
                {/* Named on wide screens; phones show the chosen tool in the hint below */}
                <span className="sr-only text-sm font-medium lg:not-sr-only">{label}</span>
              </button>
            );
          })}
        </div>
        <p className="hud-panel pointer-events-none absolute start-3 end-16 top-[4.5rem] rounded-lg px-3 py-2 text-xs text-gray-300 lg:bottom-3 lg:end-auto lg:top-auto lg:max-w-sm">
          <span className="font-semibold text-white lg:hidden">
            {tool === "remove" ? t.plan.remove : t.plan.kinds[tool]}:{" "}
          </span>
          {t.plan.hint}
        </p>
      </div>

      <aside className="w-full shrink-0 overflow-y-auto border-gray-800 bg-gray-950 p-5 lg:w-96 lg:border-s">
        <h1 className="text-2xl font-semibold tracking-tight text-white">
          {t.plan.title}
        </h1>
        {eventTitle && (
          <p className="mt-1 text-sm font-medium text-ember-300">
            {eventTitle}
          </p>
        )}
        <p className="mt-2 text-sm text-gray-300">{t.plan.intro}</p>

        <label htmlFor="pop" className="field-label mt-5">
          {t.plan.population}
        </label>
        <input
          id="pop"
          type="number"
          min={1}
          max={100000}
          step={50}
          value={population}
          onChange={(e) =>
            setPopulation(
              Math.max(0, Math.min(100_000, Number(e.target.value) || 0)),
            )
          }
          className="field tabular-nums"
        />
        <p className="mt-1.5 text-xs text-gray-400">
          {t.plan.waterNeed.replace(
            "{litres}",
            waterLitresPerDay(population).toLocaleString(lang),
          )}
        </p>

        <div className="mt-4 grid grid-cols-2 gap-2">
          <button
            type="button"
            className="btn-primary col-span-2"
            onClick={() => {
              setItems(autoLayout(center, population));
              setFitSignal((n) => n + 1);
            }}
          >
            <Sparkles className="h-4 w-4" aria-hidden="true" />
            {t.plan.autoLayout}
          </button>
          <button
            type="button"
            className="btn-ghost"
            onClick={share}
            disabled={items.length === 0}
          >
            <Link2 className="h-4 w-4" aria-hidden="true" />
            <span aria-live="polite">
              {copied ? t.plan.copied : t.plan.share}
            </span>
          </button>
          <button
            type="button"
            className="btn-ghost"
            onClick={() => setItems([])}
            disabled={items.length === 0}
          >
            <Trash2 className="h-4 w-4" aria-hidden="true" />
            {t.plan.clear}
          </button>
        </div>
        <label className="mt-3 flex items-center gap-2 text-sm text-gray-300">
          <input
            type="checkbox"
            checked={showReach}
            onChange={(e) => setShowReach(e.target.checked)}
            className="h-4 w-4 rounded border-gray-600 bg-gray-800 text-primary-500"
          />
          {t.plan.reach}
        </label>

        <PlanSaveBar
          plan={plan}
          items={items}
          population={population}
          eventId={eventId}
          defaultTitle={
            eventTitle ? `${eventTitle} — ${t.plan.title}` : t.plans.untitled
          }
          onPlan={(next) =>
            applyPlan(
              next,
              next.id !== plan?.id || next.version !== plan?.version,
            )
          }
        />

        <div className="mt-6 flex items-baseline justify-between">
          <h2 className="text-sm font-semibold text-gray-200">Sphere</h2>
          <span
            className="text-sm tabular-nums text-gray-400"
            aria-live="polite"
          >
            {met}/{kpis.length} ·{" "}
            {t.plan.itemCount.replace("{n}", String(items.length))}
          </span>
        </div>
        <ul className="divide-y divide-gray-800">
          {kpis.map((k) => (
            <KpiRow key={k.id} kpi={k} lang={lang} />
          ))}
        </ul>
        <p className="mt-4 text-xs leading-relaxed text-gray-400">
          {t.plan.disclaimer}
        </p>
        <p className="mt-2 text-xs text-gray-500">{t.plan.source}</p>
      </aside>
    </main>
  );
}

export default function PlanPage() {
  return (
    <div className="flex min-h-screen flex-col bg-gray-950 lg:h-screen">
      <Header />
      <Suspense>
        <Planner />
      </Suspense>
    </div>
  );
}
