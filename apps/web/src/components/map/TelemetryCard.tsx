"use client";

import type { ReactNode } from "react";
import { X } from "lucide-react";
import { useTranslation } from "@/lib/i18n/useTranslation";

export interface TelemetryRow {
  label: string;
  value: ReactNode;
}

interface TelemetryCardProps {
  icon: ReactNode;
  title: string;
  subtitle?: ReactNode;
  rows: TelemetryRow[];
  footer?: ReactNode;
  onClose: () => void;
}

/** Compact operations-centre style card for a tracked object (aircraft, ship, satellite) */
export function TelemetryCard({ icon, title, subtitle, rows, footer, onClose }: TelemetryCardProps) {
  const { t } = useTranslation();
  return (
    <section
      aria-label={title}
      className="pointer-events-auto w-72 rounded-lg bg-gray-900/95 text-sm text-gray-200 shadow-xl backdrop-blur"
    >
      <header className="flex items-start gap-2 px-3 py-2">
        <span className="mt-0.5 shrink-0" aria-hidden="true">
          {icon}
        </span>
        <div className="min-w-0 flex-1">
          <h2 className="truncate font-mono font-semibold text-white">{title}</h2>
          {subtitle && <p className="text-xs text-gray-400">{subtitle}</p>}
        </div>
        <button type="button" onClick={onClose} className="rounded p-1 hover:bg-gray-800" aria-label={t.common.close}>
          <X className="h-4 w-4" aria-hidden="true" />
        </button>
      </header>
      <dl className="grid grid-cols-2 gap-x-3 gap-y-1 border-t border-gray-700/60 px-3 py-2 text-xs">
        {rows.map((row) => (
          <div key={row.label} className="contents">
            <dt className="text-gray-500">{row.label}</dt>
            <dd className="text-right font-mono tabular-nums text-gray-200">{row.value}</dd>
          </div>
        ))}
      </dl>
      {footer && <p className="border-t border-gray-700/60 px-3 py-1.5 text-[11px] text-gray-500">{footer}</p>}
    </section>
  );
}
