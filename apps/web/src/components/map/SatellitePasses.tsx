"use client";

import { useEffect, useState } from "react";
import { Moon, Satellite, Sun } from "lucide-react";
import { formatAge } from "@/components/layout/SourceStatusPanel";
import { tracksAPI, type ApiSatellitePass } from "@/lib/api/client";
import { useTranslation } from "@/lib/i18n/useTranslation";

const SHOWN = 3;

/**
 * When Earth-observation satellites next pass over a place: tells responders
 * when fresh imagery can exist (optical sensors need daylight; radar does not).
 */
export function SatellitePasses({ lat, lng }: { lat: number; lng: number }) {
  const { t, lang } = useTranslation();
  const [passes, setPasses] = useState<ApiSatellitePass[] | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    setPasses(null);
    tracksAPI
      .satellitePasses(lat, lng, 24, controller.signal)
      .then(setPasses)
      .catch(() => {
        // Optional context: hide the section when orbits are unavailable
      });
    return () => controller.abort();
  }, [lat, lng]);

  if (passes === null) return null;
  const time = new Intl.DateTimeFormat(lang, { hour: "2-digit", minute: "2-digit", timeZone: "UTC" });

  return (
    <div className="mt-3 border-t border-gray-700/60 pt-2 text-xs">
      <div className="mb-1 flex items-center gap-1.5 text-gray-400">
        <Satellite className="h-3.5 w-3.5" aria-hidden="true" />
        {t.satellites.nextPasses}
      </div>
      {passes.length === 0 && <p className="text-gray-500">{t.satellites.none}</p>}
      <ul className="space-y-1">
        {passes.slice(0, SHOWN).map((pass) => (
          <li key={`${pass.noradId}-${pass.culmination}`} className="flex items-center gap-2">
            {pass.daylight ? (
              <Sun className="h-3.5 w-3.5 shrink-0 text-amber-300" aria-label={t.satellites.daylight} />
            ) : (
              <Moon className="h-3.5 w-3.5 shrink-0 text-indigo-300" aria-label={t.satellites.night} />
            )}
            <span className="flex-1 truncate text-gray-200">{pass.name}</span>
            <span className="shrink-0 tabular-nums text-gray-400" title={`${time.format(new Date(pass.culmination))} UTC`}>
              {formatAge(pass.culmination, lang)} · {Math.round(pass.maxElevationDeg)}°
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
