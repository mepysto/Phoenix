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
}: {
  icon?: LucideIcon;
  title: string;
  body?: React.ReactNode;
  action?: React.ReactNode;
  className?: string;
}) {
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
      {body && <p className="mt-1 max-w-md text-sm text-gray-400">{body}</p>}
      {action && <div className="mt-5 flex flex-wrap justify-center gap-2">{action}</div>}
    </div>
  );
}
