"use client";

import { useEffect, useState } from "react";
import { ExternalLink, Pause, Play, Radio } from "lucide-react";
import { radioAPI, type ApiRadioStation } from "@/lib/api/client";
import { useTranslation } from "@/lib/i18n/useTranslation";

const SHOWN = 3;

/**
 * Stations broadcasting near an event: emergency information in the local
 * language, and an off-air station can itself signal an outage.
 */
export function LocalRadio({ lat, lng }: { lat: number; lng: number }) {
  const { t } = useTranslation();
  const [stations, setStations] = useState<ApiRadioStation[]>([]);
  const [playing, setPlaying] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    setStations([]);
    setPlaying(null);
    radioAPI
      // The directory has sparse locations and AM carries far: search wide, show distance
      .nearby(lat, lng, 300, controller.signal)
      .then(setStations)
      .catch(() => {
        // Optional context
      });
    return () => controller.abort();
  }, [lat, lng]);

  if (stations.length === 0) return null;
  const current = stations.find((s) => s.id === playing);

  return (
    <div className="mt-3 border-t border-gray-700/60 pt-2 text-xs">
      <div className="mb-1 flex items-center gap-1.5 text-gray-400">
        <Radio className="h-3.5 w-3.5" aria-hidden="true" />
        {t.radio.title}
      </div>
      <ul className="space-y-1">
        {stations.slice(0, SHOWN).map((station) => (
          <li key={station.id} className="flex items-center gap-2">
            {station.streamUrl ? (
              <button
                type="button"
                onClick={() => setPlaying(playing === station.id ? null : station.id)}
                className="rounded p-0.5 text-gray-300 hover:bg-gray-800 hover:text-white"
                aria-label={`${playing === station.id ? t.radio.stop : t.radio.play}: ${station.name}`}
              >
                {playing === station.id ? <Pause className="h-3.5 w-3.5" /> : <Play className="h-3.5 w-3.5" />}
              </button>
            ) : station.listenUrl ? (
              <a
                href={station.listenUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="rounded p-0.5 text-gray-300 hover:bg-gray-800 hover:text-white"
                aria-label={`${t.radio.open}: ${station.name}`}
              >
                <ExternalLink className="h-3.5 w-3.5" />
              </a>
            ) : (
              <span className="w-4" />
            )}
            <span className={`flex-1 truncate ${station.onAir ? "text-gray-200" : "text-gray-500 line-through"}`}>
              {station.name}
            </span>
            {!station.onAir && <span className="shrink-0 text-amber-400">{t.radio.offAir}</span>}
            <span className="shrink-0 tabular-nums text-gray-400">{Math.round(station.distanceKm)} km</span>
          </li>
        ))}
      </ul>
      {current?.streamUrl && (
        // Streams are third-party audio; the browser connects to the station directly
        <audio src={current.streamUrl} autoPlay controls className="mt-1.5 h-8 w-full" onError={() => setPlaying(null)} />
      )}
    </div>
  );
}
