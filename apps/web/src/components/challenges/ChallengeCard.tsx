import Link from "next/link";
import { Clock, Trophy, Users } from "lucide-react";
import { VerifiedBadge } from "@/components/connect/VerifiedBadge";
import type { ChallengeSummary } from "@/lib/api/community";
import { useTranslation } from "@/lib/i18n/useTranslation";
import { formatDate } from "@/lib/format";

export function ChallengeCard({ ch }: { ch: ChallengeSummary }) {
  const { t, lang } = useTranslation();
  const c = t.challenges;
  const date = formatDate(ch.closesAt, lang);
  return (
    <Link
      href={`/challenges/${ch.id}`}
      className="block rounded-xl border border-gray-700/80 bg-gray-900 p-5 transition-colors hover:border-gray-600"
    >
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <span
          className={`rounded-full px-2 py-0.5 font-medium ${ch.isOpen ? "bg-primary-400/15 text-primary-200" : "bg-gray-800 text-gray-300"}`}
        >
          {ch.isOpen ? c.open : c.closed}
        </span>
        {ch.hasSelection && (
          <span className="flex items-center gap-1 rounded-full bg-amber-400/15 px-2 py-0.5 font-medium text-amber-200">
            <Trophy className="h-3 w-3" aria-hidden="true" />
            {c.selected}
          </span>
        )}
      </div>
      <h2 className="mt-2 text-lg font-semibold text-white">{ch.title}</h2>
      <p className="mt-1 flex items-center gap-1.5 text-sm text-gray-400">
        {c.hostedBy.replace("{org}", ch.org.name)}
        {ch.org.verified && <VerifiedBadge compact />}
      </p>
      <p className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-gray-400">
        <span className="flex items-center gap-1">
          <Users className="h-3.5 w-3.5" aria-hidden="true" />
          {c.people.replace("{n}", ch.population.toLocaleString(lang))}
        </span>
        <span className="flex items-center gap-1">
          <Clock className="h-3.5 w-3.5" aria-hidden="true" />
          {(ch.isOpen ? c.closes : c.closedOn).replace("{date}", date)}
        </span>
        <span>{c.entries.replace("{n}", String(ch.entryCount))}</span>
      </p>
    </Link>
  );
}
