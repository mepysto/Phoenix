"use client";

import { useCallback, useEffect, useState } from "react";
import { Radio, Video, X } from "lucide-react";
import { camerasAPI } from "@/lib/api/client";
import { useTranslation } from "@/lib/i18n/useTranslation";
import { LiveStream } from "./LiveStream";

const REFRESH_MS = 60_000; // the proxy caches 60 s; upstream images change every few minutes

interface CameraViewerProps {
  id: string;
  name: string;
  direction?: string | null;
  source?: string | null;
  snapshotMinutes?: number | null;
  /** Public HLS stream, when the camera has one */
  streamUrl?: string | null;
  onClose: () => void;
}

/** Latest still image of a public camera, through the API proxy */
export function CameraViewer({ id, name, direction, source, snapshotMinutes, streamUrl, onClose }: CameraViewerProps) {
  const { t } = useTranslation();
  const [tick, setTick] = useState(() => Date.now());
  const [failed, setFailed] = useState(false);
  const [live, setLive] = useState(false);
  const [liveFailed, setLiveFailed] = useState(false);
  const onLiveError = useCallback(() => {
    setLive(false);
    setLiveFailed(true);
  }, []);

  useEffect(() => {
    setFailed(false);
    setLive(false);
    setLiveFailed(false);
    setTick(Date.now());
    const timer = setInterval(() => setTick(Date.now()), REFRESH_MS);
    return () => clearInterval(timer);
  }, [id]);

  return (
    <section
      aria-label={name}
      className="pointer-events-auto w-80 overflow-hidden rounded-lg bg-gray-900/95 text-sm text-gray-200 shadow-xl backdrop-blur"
    >
      <header className="flex items-start gap-2 px-3 py-2">
        <Video className="mt-0.5 h-4 w-4 shrink-0 text-violet-300" aria-hidden="true" />
        <div className="min-w-0 flex-1">
          <h2 className="truncate font-semibold text-white" title={name}>
            {name}
          </h2>
          <p className="text-xs text-gray-400">
            {[direction, source].filter(Boolean).join(" · ")}
            {snapshotMinutes ? ` · ${t.cameras.updates.replace("{n}", String(snapshotMinutes))}` : ""}
          </p>
        </div>
        <button type="button" onClick={onClose} className="rounded p-1 hover:bg-gray-800" aria-label={t.common.close}>
          <X className="h-4 w-4" aria-hidden="true" />
        </button>
      </header>
      {streamUrl && (
        <div className="flex items-center gap-2 border-t border-gray-700/60 px-3 py-1.5 text-xs">
          <button
            type="button"
            onClick={() => {
              setLiveFailed(false);
              setLive(!live);
            }}
            aria-pressed={live}
            className={`flex items-center gap-1 rounded px-2 py-0.5 ${live ? "bg-red-700 text-white" : "border border-gray-600 text-gray-300 hover:bg-gray-800"}`}
          >
            <Radio className="h-3 w-3" aria-hidden="true" />
            {t.cameras.liveVideo}
          </button>
          {liveFailed && <span className="text-amber-300">{t.cameras.streamOffline}</span>}
        </div>
      )}
      {live && streamUrl ? (
        <LiveStream src={streamUrl} label={`${t.cameras.liveVideo}: ${name}`} onError={onLiveError} />
      ) : failed ? (
        <p className="px-3 pb-3 text-gray-400">{t.cameras.unavailable}</p>
      ) : (
        // eslint-disable-next-line @next/next/no-img-element -- proxied, frequently refreshed JPEG
        <img
          src={camerasAPI.snapshotUrl(id, tick)}
          alt={`${t.cameras.live}: ${name}`}
          className="aspect-video w-full bg-gray-800 object-cover"
          onError={() => setFailed(true)}
        />
      )}
      <p className="px-3 py-1.5 text-[11px] text-gray-500">
        {t.cameras.notRecorded}
        {direction ? ` · ${t.cameras.approxView}` : ""}
        {live ? ` · ${t.cameras.liveDirect}` : ""}
      </p>
    </section>
  );
}
