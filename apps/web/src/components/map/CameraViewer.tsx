"use client";

import { useEffect, useState } from "react";
import { Video, X } from "lucide-react";
import { camerasAPI } from "@/lib/api/client";
import { useTranslation } from "@/lib/i18n/useTranslation";

const REFRESH_MS = 60_000; // the proxy caches 60 s; upstream images change every few minutes

interface CameraViewerProps {
  id: string;
  name: string;
  direction?: string | null;
  source?: string | null;
  snapshotMinutes?: number | null;
  onClose: () => void;
}

/** Latest still image of a public camera, through the API proxy */
export function CameraViewer({ id, name, direction, source, snapshotMinutes, onClose }: CameraViewerProps) {
  const { t } = useTranslation();
  const [tick, setTick] = useState(() => Date.now());
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    setFailed(false);
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
      {failed ? (
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
      <p className="px-3 py-1.5 text-[11px] text-gray-500">{t.cameras.notRecorded}</p>
    </section>
  );
}
