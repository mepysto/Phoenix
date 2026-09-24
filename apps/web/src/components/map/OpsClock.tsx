"use client";

import { useEffect, useState } from "react";
import { useTranslation } from "@/lib/i18n/useTranslation";
import { useUiStore } from "@/store/uiStore";

/** Operations-console banner with a UTC clock (shown in Ops mode) */
export function OpsClock() {
  const { t } = useTranslation();
  const opsMode = useUiStore((s) => s.opsMode);
  const [now, setNow] = useState(() => new Date());

  useEffect(() => {
    if (!opsMode) return;
    const timer = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(timer);
  }, [opsMode]);

  if (!opsMode) return null;
  return (
    <div
      role="status"
      className="pointer-events-none rounded-md border border-emerald-700/60 bg-black/80 px-3 py-1 font-mono text-xs tracking-wider text-emerald-300 shadow-lg"
    >
      {t.ops.label} · {now.toISOString().slice(11, 19)}Z
    </div>
  );
}
