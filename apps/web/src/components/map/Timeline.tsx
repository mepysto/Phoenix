"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Pause, Play, Radio } from "lucide-react";
import { timelineAPI, type ApiTimeline } from "@/lib/api/client";
import { useTranslation } from "@/lib/i18n/useTranslation";
import {
  instantAt,
  nextPlaybackInstant,
  positionOf,
  TICK_MS,
  timelineWindow,
  WINDOW_DAYS,
} from "@/lib/timeline";
import { ALL_EVENT_TYPES, ALL_SEVERITIES, useEventStore } from "@/store/eventStore";
import { useTimelineStore } from "@/store/timelineStore";

const FILTER_THROTTLE_MS = 300;

/**
 * Time scrubber: a 30-day histogram of event onsets with a cursor. Moving
 * the cursor into the past shows the events that were ongoing at that
 * instant; the right end is "live".
 */
export function Timeline() {
  const { t, lang } = useTranslation();
  const { at, playing, speed, setAt, setPlaying, cycleSpeed } = useTimelineStore();
  const visibleTypes = useEventStore((s) => s.visibleTypes);
  const visibleSeverities = useEventStore((s) => s.visibleSeverities);
  const setFilter = useEventStore((s) => s.setFilter);
  // Fixed per mount so positions stay stable while scrubbing
  const [window] = useState(() => timelineWindow(new Date()));
  const [histogram, setHistogram] = useState<ApiTimeline | null>(null);

  // Histogram follows the type/severity filters
  useEffect(() => {
    let cancelled = false;
    const types = visibleTypes.size < ALL_EVENT_TYPES.length ? [...visibleTypes] : undefined;
    const severities =
      visibleSeverities.size < ALL_SEVERITIES.length ? [...visibleSeverities] : undefined;
    timelineAPI
      .get(window.start.toISOString(), window.end.toISOString(), "day", { types, severities })
      .then((data) => !cancelled && setHistogram(data))
      .catch(() => {
        // Histogram is decoration; the scrubber works without it
      });
    return () => {
      cancelled = true;
    };
  }, [window, visibleTypes, visibleSeverities]);

  // Apply the instant to the event query, throttled: a debounce would starve
  // during playback (ticks come faster than the delay), a throttle keeps
  // refreshing while still coalescing drag events
  const lastAppliedRef = useRef(0);
  useEffect(() => {
    const apply = () => {
      lastAppliedRef.current = Date.now();
      setFilter({ at: at ?? undefined });
    };
    const wait = FILTER_THROTTLE_MS - (Date.now() - lastAppliedRef.current);
    if (wait <= 0) {
      apply();
      return;
    }
    const timer = setTimeout(apply, wait);
    return () => clearTimeout(timer);
  }, [at, setFilter]);

  // Playback: advance until the present, then fall back to live
  useEffect(() => {
    if (!playing) return;
    const timer = setInterval(() => {
      const current = useTimelineStore.getState().at;
      useTimelineStore.getState().setAt(nextPlaybackInstant(window, current, speed));
    }, TICK_MS);
    return () => clearInterval(timer);
  }, [playing, speed, window]);

  const days = useMemo(() => {
    const counts = new Map(
      (histogram?.buckets ?? []).map((b) => [b.start.slice(0, 10), b.total]),
    );
    return Array.from({ length: WINDOW_DAYS + 1 }, (_, i) => {
      const day = new Date(window.start.getTime() + i * 86_400_000).toISOString().slice(0, 10);
      return { day, total: counts.get(day) ?? 0 };
    });
  }, [histogram, window]);
  const maxTotal = Math.max(1, ...days.map((d) => d.total));
  const position = positionOf(window, at);
  const cursorDay = Math.floor(position / 24);
  const label =
    at === null
      ? t.timeline.live
      : new Intl.DateTimeFormat(lang, { dateStyle: "medium", timeStyle: "short", timeZone: "UTC" }).format(
          new Date(at),
        ) + " UTC";

  return (
    <div className="pointer-events-auto rounded-lg bg-gray-900/90 px-3 py-2 text-xs text-gray-300 shadow-lg backdrop-blur">
      <div className="mb-1 flex items-center gap-2">
        <button
          type="button"
          onClick={() => {
            if (!playing && at === null) setAt(window.start.toISOString()); // replay from the start
            setPlaying(!playing);
          }}
          className="rounded p-1 hover:bg-gray-800"
          aria-label={playing ? t.timeline.pause : t.timeline.play}
        >
          {playing ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
        </button>
        <button
          type="button"
          onClick={cycleSpeed}
          className="w-10 rounded px-1 py-0.5 tabular-nums hover:bg-gray-800"
          aria-label={t.timeline.speed}
        >
          {speed}×
        </button>
        <span className={`flex-1 truncate ${at === null ? "text-green-400" : "text-amber-300"}`} aria-live="polite">
          {label}
        </span>
        {at !== null && (
          <button
            type="button"
            onClick={() => setAt(null)}
            className="flex items-center gap-1 rounded px-2 py-0.5 text-green-400 hover:bg-gray-800"
          >
            <Radio className="h-3 w-3" aria-hidden="true" />
            {t.timeline.backToLive}
          </button>
        )}
      </div>

      {/* Daily onset histogram; days up to the cursor are highlighted */}
      <div className="flex h-8 items-end gap-px" aria-hidden="true">
        {days.map(({ day, total }, index) => (
          <div
            key={day}
            title={`${day}: ${total}`}
            className={index <= cursorDay ? "flex-1 bg-primary-500/70" : "flex-1 bg-gray-600/60"}
            style={{ height: `${Math.max(4, (total / maxTotal) * 100)}%` }}
          />
        ))}
      </div>

      <input
        type="range"
        min={0}
        max={window.hours}
        step={1}
        value={position}
        onChange={(e) => {
          setPlaying(false);
          setAt(instantAt(window, Number(e.target.value)));
        }}
        className="w-full accent-primary-500"
        aria-label={t.timeline.scrub}
        aria-valuetext={label}
      />
    </div>
  );
}
