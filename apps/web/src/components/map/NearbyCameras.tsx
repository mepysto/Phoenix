"use client";

import { useEffect, useState } from "react";
import { Video } from "lucide-react";
import { camerasAPI, type ApiNearbyCamera } from "@/lib/api/client";
import { useTranslation } from "@/lib/i18n/useTranslation";
import { useMapStore } from "@/store/mapStore";

const SHOWN = 3;

/** Public cameras near an event; picking one opens its latest image */
export function NearbyCameras({ lat, lng }: { lat: number; lng: number }) {
  const { t } = useTranslation();
  const setInspected = useMapStore((s) => s.setInspected);
  const [cameras, setCameras] = useState<ApiNearbyCamera[]>([]);

  useEffect(() => {
    const controller = new AbortController();
    setCameras([]);
    camerasAPI
      .nearby(lat, lng, 25, controller.signal)
      .then(setCameras)
      .catch(() => {
        // Optional context; most of the world has no public camera source yet
      });
    return () => controller.abort();
  }, [lat, lng]);

  if (cameras.length === 0) return null;
  return (
    <div className="mt-3 border-t border-gray-700/60 pt-2 text-xs">
      <div className="mb-1 flex items-center gap-1.5 text-gray-400">
        <Video className="h-3.5 w-3.5" aria-hidden="true" />
        {t.cameras.nearby}
      </div>
      <ul className="space-y-1">
        {cameras.slice(0, SHOWN).map((camera) => (
          <li key={camera.id}>
            <button
              type="button"
              onClick={() =>
                setInspected({
                  layerId: "cameras",
                  properties: {
                    id: camera.id,
                    name: camera.name,
                    direction: camera.direction,
                    source: camera.source,
                    stream_url: camera.streamUrl,
                  },
                  lng,
                  lat,
                })
              }
              className="flex w-full items-center gap-2 rounded text-left hover:bg-gray-800"
            >
              <span className="flex-1 truncate text-gray-200">{camera.name}</span>
              <span className="shrink-0 tabular-nums text-gray-400">{camera.distanceKm} km</span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
