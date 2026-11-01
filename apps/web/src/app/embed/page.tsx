"use client";

import dynamic from "next/dynamic";
import { Suspense, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { PhoenixMark } from "@/components/brand/PhoenixMark";
import type { SeverityLevel } from "@/lib/api/client";
import { useTranslation } from "@/lib/i18n/useTranslation";

const EmbedMap = dynamic(() => import("@/components/embed/EmbedMap"), {
  ssr: false,
});

const SEVERITIES: SeverityLevel[] = ["low", "medium", "high", "critical"];

function Embed() {
  const { t } = useTranslation();
  const p = useSearchParams();
  const [origin, setOrigin] = useState("");
  useEffect(() => setOrigin(window.location.origin), []);
  const sev = (p.get("severity") as SeverityLevel) || "medium";
  const center = useMemo<[number, number]>(
    () => [Number(p.get("lng")) || 20, Number(p.get("lat")) || 15],
    [p],
  );
  const zoom = Number(p.get("z")) || 1.4;
  return (
    <div className="relative h-screen w-screen overflow-hidden bg-gray-950">
      {origin && (
        <EmbedMap
          minSeverity={SEVERITIES.includes(sev) ? sev : "medium"}
          center={center}
          zoom={zoom}
          origin={origin}
          openLabel={t.embed.open}
        />
      )}
      <a
        href={origin || "/"}
        target="_blank"
        rel="noopener"
        className="hud-panel absolute bottom-2 left-2 flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium text-gray-100"
      >
        <PhoenixMark className="h-4 w-4" />
        {t.embed.poweredBy}
      </a>
    </div>
  );
}

export default function EmbedPage() {
  return (
    <Suspense>
      <Embed />
    </Suspense>
  );
}
