import { BadgeCheck } from "lucide-react";
import { useTranslation } from "@/lib/i18n/useTranslation";

/** Shown next to an organisation the platform has verified as an official partner. */
export function VerifiedBadge({ compact = false }: { compact?: boolean }) {
  const { t } = useTranslation();
  return (
    <span
      title={t.badges.verifiedHelp}
      className="inline-flex items-center gap-1 rounded-full bg-primary-400/15 px-1.5 py-0.5 text-xs font-medium text-primary-200"
    >
      <BadgeCheck className="h-3.5 w-3.5" aria-hidden="true" />
      {compact ? (
        <span className="sr-only">{t.badges.verified}</span>
      ) : (
        t.badges.verified
      )}
    </span>
  );
}
