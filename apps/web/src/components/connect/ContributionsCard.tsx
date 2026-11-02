"use client";

import { useEffect, useState } from "react";
import {
  Award,
  FileText,
  GitFork,
  HandHeart,
  Handshake,
  LayoutGrid,
  Megaphone,
  Sparkles,
  type LucideIcon,
} from "lucide-react";
import { authAPI, type Contributions } from "@/lib/api/community";
import { useTranslation } from "@/lib/i18n/useTranslation";

const ICONS: Record<string, LucideIcon> = {
  first_offer: HandHeart,
  voice_of_need: FileText,
  connector: Handshake,
  steady_connector: Sparkles,
  planner: LayoutGrid,
  remixed: GitFork,
  reporter: Megaphone,
};

/** The signed-in user's own contributions and badges. */
export function ContributionsCard() {
  const { t, lang } = useTranslation();
  const b = t.badges;
  const [data, setData] = useState<Contributions | null>(null);

  useEffect(() => {
    authAPI
      .contributions()
      .then(setData)
      .catch(() => setData(null));
  }, []);

  if (!data) return null;
  return (
    <section
      className="rounded-xl border border-gray-800 bg-gray-900 p-5"
      aria-labelledby="contrib-title"
    >
      <div className="flex items-baseline justify-between gap-2">
        <h2
          id="contrib-title"
          className="flex items-center gap-2 font-semibold text-white"
        >
          <Award className="h-4 w-4 text-primary-400" aria-hidden="true" />
          {b.contributions}
        </h2>
        <span className="text-sm font-semibold tabular-nums text-primary-200">
          {b.points.replace("{n}", data.points.toLocaleString(lang))}
        </span>
      </div>
      <ul className="mt-4 grid grid-cols-1 gap-2">
        {data.badges.map((badge) => {
          const Icon = ICONS[badge.id] ?? Award;
          const name = b.names[badge.id as keyof typeof b.names] ?? badge.id;
          const help = b.help[badge.id as keyof typeof b.help] ?? "";
          return (
            <li
              key={badge.id}
              className={`flex items-center gap-3 rounded-lg border px-3 py-2 ${
                badge.earned
                  ? "border-primary-500/40 bg-primary-400/10"
                  : "border-gray-800"
              }`}
            >
              <Icon
                className={`h-4 w-4 shrink-0 ${badge.earned ? "text-primary-300" : "text-gray-600"}`}
                aria-hidden="true"
              />
              <div className="min-w-0 flex-1">
                <p
                  className={`text-sm font-medium ${badge.earned ? "text-gray-100" : "text-gray-400"}`}
                >
                  {name}
                </p>
                <p className="text-xs text-gray-400">{help}</p>
              </div>
              {!badge.earned && (
                <span className="shrink-0 text-xs tabular-nums text-gray-400">
                  {b.progress
                    .replace("{n}", String(badge.progress))
                    .replace("{target}", String(badge.target))}
                </span>
              )}
            </li>
          );
        })}
      </ul>
      <p className="mt-3 text-xs text-gray-500">{b.onlyYou}</p>
    </section>
  );
}
