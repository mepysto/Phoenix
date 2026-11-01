"use client";

import { useEffect, useMemo, useState } from "react";
import { Check, ClipboardCopy } from "lucide-react";
import { Header } from "@/components/layout/Header";
import type { SeverityLevel } from "@/lib/api/client";
import { useTranslation } from "@/lib/i18n/useTranslation";

const SEVERITIES: SeverityLevel[] = ["low", "medium", "high", "critical"];
const VIEWS = {
  world: { lat: 15, lng: 20, z: 1.4 },
  africa: { lat: 2, lng: 20, z: 2.6 },
  americas: { lat: 10, lng: -75, z: 1.8 },
  asia: { lat: 25, lng: 100, z: 2.3 },
  europe: { lat: 50, lng: 15, z: 3 },
} as const;

export default function EmbedBuilderPage() {
  const { t } = useTranslation();
  const e = t.embed;
  const [origin, setOrigin] = useState("");
  const [severity, setSeverity] = useState<SeverityLevel>("medium");
  const [view, setView] = useState<keyof typeof VIEWS>("world");
  const [height, setHeight] = useState(420);
  const [copied, setCopied] = useState(false);
  useEffect(() => setOrigin(window.location.origin), []);

  const src = useMemo(() => {
    const v = VIEWS[view];
    return `${origin}/embed?severity=${severity}&lat=${v.lat}&lng=${v.lng}&z=${v.z}`;
  }, [origin, severity, view]);
  const code = `<iframe src="${src}" title="Phoenix live disaster map" width="100%" height="${height}" style="border:0;border-radius:12px" loading="lazy" referrerpolicy="no-referrer"></iframe>`;

  return (
    <div className="flex min-h-screen flex-col bg-gray-950">
      <Header />
      <main className="flex-1 px-4 py-8 md:px-8">
        <div className="mx-auto max-w-5xl">
          <h1 className="text-3xl font-semibold tracking-tight text-white">
            {e.title}
          </h1>
          <p className="mt-2 max-w-2xl text-gray-300">{e.intro}</p>
          <div className="mt-6 grid gap-6 lg:grid-cols-[18rem_1fr]">
            <div className="space-y-4">
              <div>
                <label htmlFor="emb-sev" className="field-label">
                  {e.minSeverity}
                </label>
                <select
                  id="emb-sev"
                  className="field"
                  value={severity}
                  onChange={(ev) =>
                    setSeverity(ev.target.value as SeverityLevel)
                  }
                >
                  {SEVERITIES.map((s) => (
                    <option key={s} value={s}>
                      {(t.sidebar as Record<string, string>)[s]}+
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label htmlFor="emb-view" className="field-label">
                  {e.view}
                </label>
                <select
                  id="emb-view"
                  className="field"
                  value={view}
                  onChange={(ev) =>
                    setView(ev.target.value as keyof typeof VIEWS)
                  }
                >
                  <option value="world">{e.world}</option>
                  <option value="africa">Africa</option>
                  <option value="americas">Americas</option>
                  <option value="asia">Asia</option>
                  <option value="europe">Europe</option>
                </select>
              </div>
              <div>
                <label htmlFor="emb-h" className="field-label">
                  {e.height} ({height}px)
                </label>
                <input
                  id="emb-h"
                  type="range"
                  min={240}
                  max={720}
                  step={20}
                  value={height}
                  onChange={(ev) => setHeight(Number(ev.target.value))}
                  className="w-full accent-primary-400"
                />
              </div>
              <div>
                <label htmlFor="emb-code" className="field-label">
                  {e.code}
                </label>
                <textarea
                  id="emb-code"
                  readOnly
                  rows={6}
                  className="field font-mono text-xs"
                  value={code}
                  onFocus={(ev) => ev.target.select()}
                />
                <button
                  type="button"
                  className="btn-primary mt-2 w-full"
                  onClick={async () => {
                    try {
                      await navigator.clipboard.writeText(code);
                      setCopied(true);
                      setTimeout(() => setCopied(false), 2000);
                    } catch {
                      // Select the textarea by hand
                    }
                  }}
                >
                  {copied ? (
                    <Check className="h-4 w-4" aria-hidden="true" />
                  ) : (
                    <ClipboardCopy className="h-4 w-4" aria-hidden="true" />
                  )}
                  <span aria-live="polite">{copied ? e.copied : e.copy}</span>
                </button>
              </div>
            </div>
            <div>
              <p className="field-label">{e.preview}</p>
              {origin && (
                <iframe
                  key={src}
                  src={src}
                  title={e.preview}
                  width="100%"
                  height={height}
                  className="rounded-xl border border-gray-800"
                  loading="lazy"
                />
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
