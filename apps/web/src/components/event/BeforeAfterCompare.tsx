"use client";

import { useMemo, useState } from "react";
import { Minus, Plus, SatelliteDish } from "lucide-react";
import {
  COMPARE_MAX_ZOOM,
  compareTileUrl,
  compareZoom,
  defaultCompareDates,
  isoDate,
  tileGrid,
} from "@/lib/compare";
import { useTranslation } from "@/lib/i18n/useTranslation";

interface BeforeAfterCompareProps {
  lat: number;
  lng: number;
  type: string;
  startDate: string;
}

const MIN_ZOOM = 3;

function Mosaic({
  date,
  lat,
  lng,
  z,
  label,
}: {
  date: string;
  lat: number;
  lng: number;
  z: number;
  label: string;
}) {
  const { t } = useTranslation();
  const grid = useMemo(() => tileGrid(lat, lng, z), [lat, lng, z]);
  const key = `${date}/${z}/${lat}/${lng}`;
  // Failed tiles for the current date and zoom; reset when either changes
  const [failed, setFailed] = useState<{ key: string; n: number }>({
    key,
    n: 0,
  });
  const failures = failed.key === key ? failed.n : 0;
  return (
    <>
      {failures >= grid.tiles.length && (
        <div className="absolute inset-0 flex items-center justify-center p-6 text-center text-sm text-gray-400">
          {t.compare.unavailable.replace("{date}", date)}
        </div>
      )}
      <div
        className="absolute left-1/2 top-1/2 h-[768px] w-[768px]"
        style={{
          transform: `translate(${-grid.focus.x}px, ${-grid.focus.y}px)`,
        }}
        role="img"
        aria-label={label}
      >
        {grid.tiles.map((tile) => (
          // eslint-disable-next-line @next/next/no-img-element -- remote WMTS tiles, sized exactly
          <img
            key={`${date}-${z}-${tile.x}-${tile.y}`}
            src={compareTileUrl(date, z, tile)}
            alt=""
            width={256}
            height={256}
            loading="lazy"
            draggable={false}
            onError={(e) => {
              // Hide the broken-image frame; count it toward "unavailable"
              e.currentTarget.style.visibility = "hidden";
              setFailed((f) => ({ key, n: (f.key === key ? f.n : 0) + 1 }));
            }}
            className="absolute h-[256px] w-[256px] select-none"
            style={{ left: tile.col * 256, top: tile.row * 256 }}
          />
        ))}
      </div>
    </>
  );
}

/**
 * Drag-to-compare satellite view of the event area: the day before onset on
 * the left, a day after on the right. Keyboard: focus the slider and use the
 * arrow keys.
 */
export function BeforeAfterCompare({
  lat,
  lng,
  type,
  startDate,
}: BeforeAfterCompareProps) {
  const { t } = useTranslation();
  const defaults = useMemo(
    () => defaultCompareDates(new Date(startDate)),
    [startDate],
  );
  const [before, setBefore] = useState(defaults.before);
  const [after, setAfter] = useState(defaults.after);
  const [split, setSplit] = useState(50);
  const [z, setZ] = useState(() => compareZoom(type));
  const maxDate = isoDate(new Date(Date.now() - 86_400_000));

  return (
    <section
      className="overflow-hidden rounded-xl border border-gray-800 bg-gray-900"
      aria-labelledby="compare-title"
    >
      <header className="flex flex-wrap items-center justify-between gap-3 px-5 pb-3 pt-4">
        <div className="flex items-center gap-2">
          <SatelliteDish
            className="h-4 w-4 text-primary-400"
            aria-hidden="true"
          />
          <h2 id="compare-title" className="text-base font-semibold text-white">
            {t.compare.title}
          </h2>
        </div>
        <div className="flex items-center gap-2 text-xs">
          <label className="flex items-center gap-1.5 text-gray-400">
            {t.compare.before}
            <input
              type="date"
              value={before}
              max={after}
              onChange={(e) => e.target.value && setBefore(e.target.value)}
              className="rounded-md border border-gray-700 bg-gray-800 px-2 py-1 text-gray-100"
            />
          </label>
          <label className="flex items-center gap-1.5 text-gray-400">
            {t.compare.after}
            <input
              type="date"
              value={after}
              min={before}
              max={maxDate}
              onChange={(e) => e.target.value && setAfter(e.target.value)}
              className="rounded-md border border-gray-700 bg-gray-800 px-2 py-1 text-gray-100"
            />
          </label>
        </div>
      </header>

      <div className="relative h-72 overflow-hidden bg-gray-950 md:h-96">
        <Mosaic
          date={before}
          lat={lat}
          lng={lng}
          z={z}
          label={`${t.compare.before} ${before}`}
        />
        <div
          className="absolute inset-0"
          style={{ clipPath: `inset(0 0 0 ${split}%)` }}
        >
          <Mosaic
            date={after}
            lat={lat}
            lng={lng}
            z={z}
            label={`${t.compare.after} ${after}`}
          />
        </div>

        {/* Event position */}
        <span
          aria-hidden="true"
          className="pointer-events-none absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2"
        >
          <span className="absolute -inset-3 animate-ring-pulse rounded-full border border-ember-400" />
          <span className="block h-2.5 w-2.5 rounded-full bg-ember-500 ring-2 ring-gray-950" />
        </span>

        <input
          type="range"
          min={0}
          max={100}
          step={1}
          value={split}
          onChange={(e) => setSplit(Number(e.target.value))}
          aria-label={t.compare.sliderLabel}
          aria-valuetext={`${t.compare.before} ${split}% · ${t.compare.after} ${100 - split}%`}
          className="peer absolute inset-0 z-10 h-full w-full cursor-ew-resize opacity-0"
        />
        {/* Divider (after the slider so it can show the slider's focus) */}
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-y-0 w-px bg-white/80 peer-focus-visible:w-0.5 peer-focus-visible:bg-primary-300"
          style={{ left: `${split}%` }}
        >
          <span className="absolute left-1/2 top-1/2 flex h-8 w-8 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full border border-white/70 bg-gray-950/80 text-[10px] text-white">
            ⟷
          </span>
        </div>
        <span className="pointer-events-none absolute left-3 top-3 rounded bg-gray-950/80 px-2 py-0.5 text-xs text-gray-100">
          {t.compare.before} · {before}
        </span>
        <span className="pointer-events-none absolute right-3 top-3 rounded bg-gray-950/80 px-2 py-0.5 text-xs text-gray-100">
          {t.compare.after} · {after}
        </span>

        <div className="absolute bottom-3 right-3 z-20 flex flex-col overflow-hidden rounded-md border border-gray-700 bg-gray-950/85">
          <button
            type="button"
            onClick={() => setZ((v) => Math.min(COMPARE_MAX_ZOOM, v + 1))}
            disabled={z >= COMPARE_MAX_ZOOM}
            aria-label={t.compare.zoomIn}
            title={t.compare.zoomIn}
            className="p-1.5 text-gray-200 hover:bg-gray-800 disabled:text-gray-600"
          >
            <Plus className="h-4 w-4" aria-hidden="true" />
          </button>
          <button
            type="button"
            onClick={() => setZ((v) => Math.max(MIN_ZOOM, v - 1))}
            disabled={z <= MIN_ZOOM}
            aria-label={t.compare.zoomOut}
            title={t.compare.zoomOut}
            className="border-t border-gray-700 p-1.5 text-gray-200 hover:bg-gray-800 disabled:text-gray-600"
          >
            <Minus className="h-4 w-4" aria-hidden="true" />
          </button>
        </div>
      </div>
      <p className="px-5 py-3 text-xs text-gray-400">
        {t.compare.note} {t.compare.credit}
      </p>
    </section>
  );
}
