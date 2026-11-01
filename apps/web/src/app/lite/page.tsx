import type { Metadata } from "next";
import { headers } from "next/headers";
import Link from "next/link";
import { SEVERITY_COLORS } from "@phoenix/shared/constants";
import { translations } from "@/lib/i18n/translations";
import type { Language } from "@/store/settingsStore";

/**
 * Text-only list of active disasters for slow or metered connections
 * (PRD NFR-6). Rendered on the server: no map, no client-side data fetch,
 * a few kilobytes of HTML.
 */

export const dynamic = "force-dynamic";
export const metadata: Metadata = { title: "Phoenix — text version" };

const API =
  process.env.API_INTERNAL_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  "http://localhost:28000";
const LANGS = Object.keys(translations) as Language[];
const RANK: Record<string, number> = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
};

interface LiteEvent {
  id: string;
  type: string;
  title: string;
  severity: string;
  start_date: string;
  affected_population: number | null;
  source_url?: string | null;
  location: { country: string | null };
}

function pickLang(param: string | undefined, accept: string | null): Language {
  if (param && LANGS.includes(param as Language)) return param as Language;
  for (const part of (accept ?? "").split(",")) {
    const code = part.trim().slice(0, 2).toLowerCase();
    if (LANGS.includes(code as Language)) return code as Language;
  }
  return "en";
}

async function load(): Promise<LiteEvent[] | null> {
  try {
    const r = await fetch(`${API}/api/v1/events?is_active=true&limit=200`, {
      cache: "no-store",
    });
    if (!r.ok) return null;
    return ((await r.json()) as { data: LiteEvent[] }).data;
  } catch {
    return null;
  }
}

export default async function LitePage({
  searchParams,
}: {
  searchParams: Promise<{ lang?: string }>;
}) {
  const lang = pickLang(
    (await searchParams).lang,
    (await headers()).get("accept-language"),
  );
  const t = translations[lang];
  const events = await load();
  const sorted = (events ?? []).sort(
    (a, b) =>
      (RANK[a.severity] ?? 9) - (RANK[b.severity] ?? 9) ||
      b.start_date.localeCompare(a.start_date),
  );
  const now = new Date().toISOString().slice(0, 16).replace("T", " ");
  const label = (k: string) => (t.sidebar as Record<string, string>)[k] ?? k;

  return (
    <main
      lang={lang}
      dir={lang === "ar" ? "rtl" : "ltr"}
      className="mx-auto max-w-2xl px-4 py-6 text-gray-100"
    >
      <header className="border-b border-gray-800 pb-4">
        <h1 className="text-2xl font-semibold">Phoenix · {t.lite.title}</h1>
        <p className="mt-1 text-sm text-gray-400">
          {t.lite.intro} {t.lite.updated.replace("{time}", now)}
        </p>
        <nav className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-sm">
          <Link
            href="/"
            prefetch={false}
            className="text-primary-300 underline"
          >
            {t.lite.full}
          </Link>
          {LANGS.map((l) => (
            <a
              key={l}
              href={`/lite?lang=${l}`}
              aria-current={l === lang ? "true" : undefined}
              className={
                l === lang ? "font-semibold" : "text-gray-400 underline"
              }
            >
              {l.toUpperCase()}
            </a>
          ))}
        </nav>
      </header>
      {events === null ? (
        <p role="alert" className="mt-6 text-ember-300">
          {t.lite.error}
        </p>
      ) : sorted.length === 0 ? (
        <p className="mt-6 text-gray-300">{t.lite.none}</p>
      ) : (
        <>
          <p className="mt-4 text-sm text-gray-400">
            {t.lite.count.replace("{n}", String(sorted.length))}
          </p>
          <ol className="mt-2 divide-y divide-gray-800">
            {sorted.map((e) => (
              <li key={e.id} className="py-3">
                <p>
                  <span
                    className="mr-2 inline-block h-2.5 w-2.5 rounded-full align-middle"
                    style={{
                      backgroundColor:
                        SEVERITY_COLORS[
                          e.severity as keyof typeof SEVERITY_COLORS
                        ] ?? "#888",
                    }}
                    aria-hidden="true"
                  />
                  <strong>{label(e.severity)}</strong> · {label(e.type)}
                  {e.location.country ? ` · ${e.location.country}` : ""}
                </p>
                <p className="mt-0.5">
                  <a href={`/events/${e.id}`} className="underline">
                    {e.title}
                  </a>
                </p>
                <p className="text-sm text-gray-400">
                  {e.start_date.slice(0, 10)}
                  {e.affected_population
                    ? ` · ${t.lite.affected.replace("{n}", e.affected_population.toLocaleString(lang))}`
                    : ""}
                </p>
              </li>
            ))}
          </ol>
        </>
      )}
    </main>
  );
}
