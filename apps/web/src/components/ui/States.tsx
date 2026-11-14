"use client";

import type { LucideIcon } from "lucide-react";
import { PhoenixMark } from "@/components/brand/PhoenixMark";
import { useTranslation } from "@/lib/i18n/useTranslation";

/**
 * One loading look for whole screens and map engines: the brand mark
 * breathing, not a generic spinner. Lists use skeletons instead.
 */
export function BrandLoader({
  label,
  className = "",
}: {
  label?: string;
  className?: string;
}) {
  const { t } = useTranslation();
  return (
    <div
      role="status"
      className={`flex h-full w-full flex-col items-center justify-center gap-4 bg-gray-950 ${className}`}
    >
      <span className="relative flex h-14 w-14 items-center justify-center">
        <span
          aria-hidden="true"
          className="absolute inset-0 animate-ring-pulse rounded-full border border-primary-400/50"
        />
        <PhoenixMark className="h-9 w-9 animate-pulse" />
      </span>
      <p className="text-sm text-gray-400">{label ?? t.common.loading}</p>
    </div>
  );
}

/** Empty and filtered-to-zero results: say what is missing and offer the next step */
export function EmptyState({
  icon: Icon,
  title,
  body,
  action,
  className = "",
  compact = false,
}: {
  icon?: LucideIcon;
  title: string;
  body?: React.ReactNode;
  action?: React.ReactNode;
  className?: string;
  /** Inside a card or side panel: one quiet row instead of a dashed block */
  compact?: boolean;
}) {
  if (compact) {
    return (
      <div
        className={`flex items-start gap-3 rounded-lg bg-gray-950/50 px-3 py-3 ${className}`}
      >
        {Icon && (
          <Icon
            className="mt-0.5 h-4 w-4 shrink-0 text-gray-500"
            aria-hidden="true"
          />
        )}
        <div className="min-w-0 text-sm">
          <p className="text-gray-300">{title}</p>
          {body &&
            (typeof body === "string" ? (
              <p className="mt-0.5 text-xs text-gray-400">{body}</p>
            ) : (
              <div className="mt-0.5 text-xs text-gray-400">{body}</div>
            ))}
          {action && <div className="mt-2 flex flex-wrap gap-2">{action}</div>}
        </div>
      </div>
    );
  }
  return (
    <div
      className={`flex flex-col items-center rounded-xl border border-dashed border-gray-700 px-6 py-10 text-center ${className}`}
    >
      {Icon && (
        <span className="mb-3 flex h-11 w-11 items-center justify-center rounded-full bg-gray-800/70 text-gray-400">
          <Icon className="h-5 w-5" aria-hidden="true" />
        </span>
      )}
      <p className="font-medium text-gray-200">{title}</p>
      {/* A paragraph for text; a block for richer bodies (lists cannot sit inside <p>) */}
      {body &&
        (typeof body === "string" ? (
          <p className="mt-1 max-w-md text-sm text-gray-400">{body}</p>
        ) : (
          <div className="mt-1 max-w-md text-sm text-gray-400">{body}</div>
        ))}
      {action && (
        <div className="mt-5 flex flex-wrap justify-center gap-2">{action}</div>
      )}
    </div>
  );
}
