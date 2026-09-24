"use client";

import { useEffect, useRef, useState } from "react";
import { ChevronLeft, ChevronRight, Link2, Pause, Play, X } from "lucide-react";
import { decodeBrief, encodeBrief } from "@/lib/brief";
import { useTranslation } from "@/lib/i18n/useTranslation";
import { useBriefStore } from "@/store/briefStore";
import { useMapStore } from "@/store/mapStore";
import { useTimelineStore } from "@/store/timelineStore";

const BRIEF_PARAM = "brief";

function setBriefParam(value: string | null) {
  const params = new URLSearchParams(window.location.search);
  if (value === null) params.delete(BRIEF_PARAM);
  else params.set(BRIEF_PARAM, value);
  const qs = params.toString().replace(/%2C/gi, ",").replace(/%3A/gi, ":");
  window.history.replaceState(window.history.state, "", `${window.location.pathname}${qs ? `?${qs}` : ""}`);
}

/**
 * Plays a Disaster Brief: each scene moves the camera, sets the timeline
 * instant and the overlays, then advances. Closing restores what the user
 * had before. Opens automatically from a shared ?brief= link.
 */
export function BriefPlayer() {
  const { t } = useTranslation();
  const { brief, index, playing, start, goTo, setPlaying, stop } = useBriefStore();
  const [copied, setCopied] = useState(false);
  // What the map looked like before the brief, restored on close
  const saved = useRef<{ overlays: string[]; at: string | null } | null>(null);

  // A shared link starts the brief
  useEffect(() => {
    const shared = decodeBrief(new URLSearchParams(window.location.search).get(BRIEF_PARAM));
    if (shared) start(shared);
  }, [start]);

  // Remember the user's map on start; restore it on close
  useEffect(() => {
    if (brief && !saved.current) {
      saved.current = {
        overlays: useMapStore.getState().layers.filter((l) => l.visible).map((l) => l.id),
        at: useTimelineStore.getState().at,
      };
    }
    if (!brief && saved.current) {
      useMapStore.getState().showOnlyOverlays(saved.current.overlays);
      useTimelineStore.getState().setAt(saved.current.at);
      saved.current = null;
      setBriefParam(null);
    }
  }, [brief]);

  // Apply the current scene
  useEffect(() => {
    const scene = brief?.scenes[index];
    if (!scene) return;
    useMapStore.getState().requestCamera(scene.view);
    useTimelineStore.getState().setAt(scene.at);
    useMapStore.getState().showOnlyOverlays(scene.layers);
  }, [brief, index]);

  // Auto-advance; stay on the last scene when done
  useEffect(() => {
    const scene = brief?.scenes[index];
    if (!brief || !scene || !playing) return;
    const timer = setTimeout(() => {
      if (index < brief.scenes.length - 1) goTo(index + 1);
      else setPlaying(false);
    }, scene.durationMs);
    return () => clearTimeout(timer);
  }, [brief, index, playing, goTo, setPlaying]);

  useEffect(() => {
    if (!brief) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;
      if (e.key === "Escape") stop();
      if (e.key === "ArrowRight") goTo(useBriefStore.getState().index + 1);
      if (e.key === "ArrowLeft") goTo(useBriefStore.getState().index - 1);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [brief, goTo, stop]);

  const scene = brief?.scenes[index];
  if (!brief || !scene) return null;
  const last = brief.scenes.length - 1;

  const share = async () => {
    const encoded = encodeBrief(brief);
    setBriefParam(encoded);
    try {
      await navigator.clipboard.writeText(window.location.href);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard blocked: the link is still in the address bar
    }
  };

  const iconButton = "rounded p-1 hover:bg-gray-800 disabled:opacity-30";
  return (
    <section
      aria-label={brief.title}
      className="pointer-events-auto w-full rounded-lg bg-gray-900/95 px-4 py-3 text-sm text-gray-200 shadow-xl backdrop-blur"
    >
      <div className="flex items-start gap-2">
        <h2 className="flex-1 truncate font-semibold text-white">{brief.title}</h2>
        <button type="button" onClick={share} className={iconButton} aria-label={t.brief.share}>
          <Link2 className="h-4 w-4" aria-hidden="true" />
        </button>
        <button type="button" onClick={stop} className={iconButton} aria-label={t.brief.close}>
          <X className="h-4 w-4" aria-hidden="true" />
        </button>
      </div>
      <p className="mt-1 min-h-[2.5rem] text-gray-300" aria-live="polite">
        {copied ? t.brief.linkCopied : scene.caption}
      </p>
      <div className="mt-2 flex items-center gap-2">
        <button type="button" onClick={() => goTo(index - 1)} disabled={index === 0} className={iconButton} aria-label={t.brief.prev}>
          <ChevronLeft className="h-4 w-4" aria-hidden="true" />
        </button>
        <button
          type="button"
          onClick={() => (index === last && !playing ? (goTo(0), setPlaying(true)) : setPlaying(!playing))}
          className={iconButton}
          aria-label={playing ? t.brief.pause : t.brief.resume}
        >
          {playing ? <Pause className="h-4 w-4" aria-hidden="true" /> : <Play className="h-4 w-4" aria-hidden="true" />}
        </button>
        <button type="button" onClick={() => goTo(index + 1)} disabled={index === last} className={iconButton} aria-label={t.brief.next}>
          <ChevronRight className="h-4 w-4" aria-hidden="true" />
        </button>
        <div className="flex flex-1 justify-center gap-1.5" role="list" aria-label={t.brief.scene.replace("{n}", String(index + 1)).replace("{total}", String(last + 1))}>
          {brief.scenes.map((_, i) => (
            <button
              key={i}
              type="button"
              role="listitem"
              onClick={() => goTo(i)}
              aria-current={i === index ? "step" : undefined}
              aria-label={t.brief.scene.replace("{n}", String(i + 1)).replace("{total}", String(last + 1))}
              className={`h-2 w-2 rounded-full ${i === index ? "bg-primary-400" : i < index ? "bg-gray-400" : "bg-gray-600"}`}
            />
          ))}
        </div>
      </div>
    </section>
  );
}
