"use client";

import { useId, useState } from "react";
import { compactNumber } from "@/lib/format";
import { useTranslation } from "@/lib/i18n/useTranslation";

/*
 * Small chart kit for the overview dashboard, following one set of rules:
 * thin marks (bars <= 24px, 4px rounded data-ends, square at the baseline),
 * 2px surface gaps, recessive hairline grid, text in text tokens (never the
 * series colour), a hover/focus tooltip on every mark, and a table view for
 * every chart so no value depends on colour or hovering.
 */

export const compact = compactNumber;
export const full = (n: number, lang: string) =>
  new Intl.NumberFormat(lang).format(n);

type Tip = { x: number; y: number; value: string; label: string } | null;

/** One tooltip per chart: value first (strong), label second */
function Tooltip({ tip }: { tip: Tip }) {
  if (!tip) return null;
  return (
    <div
      role="presentation"
      className="pointer-events-none absolute z-10 -translate-x-1/2 -translate-y-full whitespace-nowrap rounded-md border border-gray-700 bg-gray-950 px-2.5 py-1.5 text-xs shadow-panel"
      style={{ left: tip.x, top: tip.y - 8 }}
    >
      <span className="block font-semibold tabular-nums text-white">
        {tip.value}
      </span>
      <span className="block text-gray-400">{tip.label}</span>
    </div>
  );
}

/** Pointer and keyboard focus show the same readout */
function useTip() {
  const [tip, setTip] = useState<Tip>(null);
  const bind = (value: string, label: string) => {
    const show = (el: HTMLElement) => {
      const box = el.getBoundingClientRect();
      const host = el.closest("[data-chart]")!.getBoundingClientRect();
      setTip({
        x: box.left - host.left + box.width / 2,
        y: box.top - host.top,
        value,
        label,
      });
    };
    return {
      tabIndex: 0,
      "aria-label": `${label}: ${value}`,
      onPointerEnter: (e: React.PointerEvent<HTMLElement>) =>
        show(e.currentTarget),
      onFocus: (e: React.FocusEvent<HTMLElement>) => show(e.currentTarget),
      onPointerLeave: () => setTip(null),
      onBlur: () => setTip(null),
    };
  };
  return { tip, bind };
}

/** Card with title, optional subtitle, and a "show as table" switch under the chart */
export function ChartCard({
  title,
  subtitle,
  table,
  children,
  className = "",
}: {
  title: string;
  subtitle?: string;
  table?: { head: string[]; rows: (string | number)[][] };
  children: React.ReactNode;
  className?: string;
}) {
  const { t } = useTranslation();
  const [showTable, setShowTable] = useState(false);
  const id = useId();
  return (
    <section
      aria-labelledby={`${id}-title`}
      className={`flex min-w-0 flex-col rounded-xl border border-gray-700/80 bg-gray-900 p-5 ${className}`}
    >
      <h2 id={`${id}-title`} className="font-semibold text-white">
        {title}
      </h2>
      {subtitle && <p className="mt-0.5 text-xs text-gray-400">{subtitle}</p>}
      <div className="mt-4 flex-1">{children}</div>
      {table && (
        <>
          <button
            type="button"
            onClick={() => setShowTable((s) => !s)}
            aria-expanded={showTable}
            aria-controls={`${id}-table`}
            className="mt-4 self-start text-xs font-medium text-gray-400 hover:text-white"
          >
            {showTable ? t.dashboard.hideTable : t.dashboard.showTable}
          </button>
          {showTable && (
            <div id={`${id}-table`} className="mt-2 overflow-x-auto">
              <table className="w-full text-start text-xs">
                <thead>
                  <tr className="border-b border-gray-800 text-gray-400">
                    {table.head.map((h, i) => (
                      <th
                        key={h}
                        scope="col"
                        className={`py-1.5 font-medium ${i ? "text-end" : "text-start"}`}
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="tabular-nums text-gray-200">
                  {table.rows.map((row, r) => (
                    <tr
                      key={r}
                      className="border-b border-gray-800/60 last:border-0"
                    >
                      {row.map((cell, i) => (
                        <td
                          key={i}
                          className={`py-1.5 ${i ? "text-end" : "text-start"}`}
                        >
                          {cell}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </section>
  );
}

/** Stat tile: label, value, optional note or delta line */
export function StatTile({
  label,
  value,
  note,
  noteTone = "muted",
  pending = false,
}: {
  label: string;
  value: string;
  note?: string;
  noteTone?: "muted" | "up-bad" | "down-good";
  /** The value is a "not yet counted" message, not a figure */
  pending?: boolean;
}) {
  const tone =
    noteTone === "up-bad"
      ? "text-ember-300"
      : noteTone === "down-good"
        ? "text-primary-300"
        : "text-gray-400";
  return (
    <div className="rounded-xl border border-gray-700/80 bg-gray-900 px-4 py-3.5">
      <p className="text-xs font-medium text-gray-400">{label}</p>
      <p
        className={
          pending
            ? "mt-2 text-base font-medium text-gray-300"
            : "mt-1 text-2xl font-semibold text-white"
        }
      >
        {value}
      </p>
      {note && <p className={`mt-0.5 text-xs ${tone}`}>{note}</p>}
    </div>
  );
}

/** Columns over time: one series; the latest column carries the accent and its value */
export function ColumnChart({
  data,
  label,
  valueLabel,
}: {
  data: { key: string; label: string; value: number }[];
  label: (d: { label: string }) => string;
  valueLabel: (v: number) => string;
}) {
  const { lang } = useTranslation();
  const { tip, bind } = useTip();
  const max = Math.max(1, ...data.map((d) => d.value));
  const step = niceStep(max);
  const top = Math.ceil(max / step) * step;
  const ticks = Array.from(
    { length: Math.round(top / step) + 1 },
    (_, i) => i * step,
  );
  const last = data.length - 1;
  return (
    <div data-chart className="relative">
      <div className="relative h-44 ps-8">
        {ticks.map((v) => (
          <div
            key={v}
            aria-hidden="true"
            className="absolute inset-x-0 border-t border-gray-800"
            style={{ bottom: `${(v / top) * 100}%` }}
          >
            <span className="absolute -top-2 start-0 text-xs tabular-nums text-gray-400">
              {compact(v, lang)}
            </span>
          </div>
        ))}
        <div className="relative flex h-full items-end gap-[2px] ps-1">
          {data.map((d, i) => (
            <div
              key={d.key}
              className="flex h-full flex-1 items-end justify-center"
            >
              <div
                {...bind(valueLabel(d.value), label(d))}
                className={`relative w-full max-w-6 rounded-t outline-offset-2 transition-opacity hover:opacity-80 ${
                  i === last
                    ? "bg-primary-400 [html.light_&]:bg-primary-600"
                    : "bg-primary-400/45 [html.light_&]:bg-primary-600/45"
                }`}
                style={{
                  height: `${(d.value / top) * 100}%`,
                  minHeight: d.value ? 2 : 0,
                }}
              >
                {i === last && (
                  <span className="absolute -top-5 left-1/2 -translate-x-1/2 text-xs font-semibold text-white">
                    {d.value}
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
      <div
        aria-hidden="true"
        className="mt-1.5 flex justify-between ps-9 text-xs text-gray-400"
      >
        <span>{data[0]?.label}</span>
        <span>{data[last]?.label}</span>
      </div>
      <Tooltip tip={tip} />
    </div>
  );
}

function niceStep(max: number) {
  const raw = max / 4;
  const pow = 10 ** Math.floor(Math.log10(raw || 1));
  const n = raw / pow;
  return (n <= 1 ? 1 : n <= 2 ? 2 : n <= 5 ? 5 : 10) * pow;
}

/** Ranked horizontal bars, one hue, largest first, value at the tip */
export function RankedBars({
  data,
  color = "bg-primary-400 [html.light_&]:bg-primary-600",
  format,
}: {
  data: { key: string; label: string; value: number; detail?: string }[];
  color?: string;
  format: (v: number) => string;
}) {
  const { tip, bind } = useTip();
  const max = Math.max(1, ...data.map((d) => d.value));
  return (
    <div data-chart className="relative">
      <ul className="space-y-2.5">
        {data.map((d) => (
          <li
            key={d.key}
            className="grid grid-cols-[minmax(6rem,9rem)_1fr] items-center gap-3 text-xs"
          >
            <span className="truncate text-gray-300" title={d.label}>
              {d.label}
            </span>
            <span className="flex items-center gap-2">
              <span
                {...bind(format(d.value), d.detail ?? d.label)}
                className={`h-3 rounded-e outline-offset-2 transition-opacity hover:opacity-80 ${color}`}
                style={{
                  width: `${Math.max((d.value / max) * 85, d.value ? 1 : 0)}%`,
                }}
              />
              <span className="shrink-0 tabular-nums text-gray-200">
                {format(d.value)}
              </span>
            </span>
          </li>
        ))}
      </ul>
      <Tooltip tip={tip} />
    </div>
  );
}

/** One whole split into ordered parts: 28px blocks, share printed where it fits, legend of names */
export function SegmentedBar({
  data,
  total,
}: {
  data: {
    key: string;
    label: string;
    value: number;
    color: string;
    darkInk?: boolean;
  }[];
  total: number;
}) {
  const { lang } = useTranslation();
  const { tip, bind } = useTip();
  const pct = (v: number) => (total ? Math.round((v / total) * 100) : 0);
  const parts = data.filter((d) => d.value > 0);
  return (
    <div data-chart className="relative">
      <div className="flex h-7 gap-[2px]">
        {parts.map((d) => (
          <div
            key={d.key}
            {...bind(`${full(d.value, lang)} · ${pct(d.value)}%`, d.label)}
            className="flex items-center overflow-hidden rounded px-2 text-xs font-semibold outline-offset-2 transition-opacity hover:opacity-85"
            // Text inside a fill: white or near-black by the fill's luminance, same in both themes
            style={{
              flexGrow: d.value,
              flexBasis: 0,
              backgroundColor: d.color,
              color: d.darkInk ? "#0a111d" : "#ffffff",
            }}
          >
            {/* Printed only when it fits: ~4 characters need ~10% of the bar */}
            {pct(d.value) >= 10 && <span>{pct(d.value)}%</span>}
          </div>
        ))}
      </div>
      <ul className="mt-3 flex flex-wrap gap-x-4 gap-y-1.5 text-xs text-gray-300">
        {data.map((d) => (
          <li key={d.key} className="flex items-center gap-1.5">
            <span
              aria-hidden="true"
              className="h-2.5 w-2.5 rounded-sm"
              style={{ backgroundColor: d.color }}
            />
            {d.label}
          </li>
        ))}
      </ul>
      <Tooltip tip={tip} />
    </div>
  );
}
