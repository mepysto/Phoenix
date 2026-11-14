"use client";

import { useEffect, useRef, useState } from "react";
import { ChevronDown } from "lucide-react";
import { SourceStatusPanel } from "@/components/layout/SourceStatusPanel";
import { useTranslation } from "@/lib/i18n/useTranslation";

/**
 * "Live" badge; opening it shows how fresh each data source is (moved out of
 * the filter panel, UX plan 5.1).
 */
export function LiveStatus({ status }: { status: "live" | "reconnecting" }) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const root = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const close = (e: Event) => {
      if (e instanceof KeyboardEvent && e.key !== "Escape") return;
      if (e instanceof MouseEvent && root.current?.contains(e.target as Node)) return;
      setOpen(false);
    };
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", close);
    return () => {
      document.removeEventListener("mousedown", close);
      document.removeEventListener("keydown", close);
    };
  }, [open]);

  return (
    <div ref={root} className="pointer-events-auto relative">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        aria-controls="source-status"
        className="hud-panel flex items-center gap-2 rounded-full px-3 py-1 text-xs font-medium text-gray-200 hover:bg-gray-800"
      >
        <span aria-hidden="true" className="relative flex h-2 w-2">
          {status === "live" && <span className="absolute inset-0 animate-ring-pulse rounded-full bg-primary-400" />}
          <span
            className={`relative h-2 w-2 rounded-full ${status === "live" ? "bg-primary-400" : "animate-pulse bg-amber-400"}`}
          />
        </span>
        <span role="status">{status === "live" ? t.map.live : t.map.reconnecting}</span>
        <ChevronDown className={`h-3.5 w-3.5 text-gray-400 transition-transform ${open ? "rotate-180" : ""}`} aria-hidden="true" />
      </button>
      {open && (
        <div id="source-status" className="hud-panel absolute left-0 top-full z-50 mt-2 w-72 animate-panel-in rounded-xl p-3">
          <SourceStatusPanel bare />
        </div>
      )}
    </div>
  );
}
