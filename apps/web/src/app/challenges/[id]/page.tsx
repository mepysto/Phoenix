"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  ArrowLeft,
  Check,
  Clock,
  ExternalLink,
  ThumbsUp,
  Trophy,
  Users,
  LayoutGrid,
} from "lucide-react";
import { EmptyState } from "@/components/ui/States";
import { Header } from "@/components/layout/Header";
import { VerifiedBadge } from "@/components/connect/VerifiedBadge";
import {
  challengesAPI,
  plansAPI,
  type ChallengeOut,
  type PlanSummary,
} from "@/lib/api/community";
import { useTranslation } from "@/lib/i18n/useTranslation";
import { evaluate, fromWire } from "@/lib/sphere";
import { useAuthStore } from "@/store/authStore";

/** Sphere checks met by each entry, measured against the challenge's population */
function useSphereScores(ch: ChallengeOut | null): Record<string, number> {
  const [scores, setScores] = useState<Record<string, number>>({});
  const ids =
    ch?.entries
      .slice(0, 20)
      .map((e) => e.planId)
      .join(",") ?? "";
  useEffect(() => {
    if (!ch) return;
    let cancelled = false;
    Promise.all(
      ch.entries.slice(0, 20).map(async (e) => {
        try {
          const plan = await plansAPI.get(e.planId);
          const kpis = evaluate({
            population: ch.population,
            items: fromWire(plan.items as [number, number, number][]),
          });
          return [
            e.planId,
            kpis.filter((k) => k.status === "ok").length,
          ] as const;
        } catch {
          return null;
        }
      }),
    ).then((rows) => {
      if (!cancelled)
        setScores(
          Object.fromEntries(
            rows.filter((r): r is readonly [string, number] => r !== null),
          ),
        );
    });
    return () => {
      cancelled = true;
    };
    // Recompute when the set of entries changes, not on every vote
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ids, ch?.population]);
  return scores;
}

export default function ChallengePage() {
  const { t, lang } = useTranslation();
  const c = t.challenges;
  const id = useParams().id as string;
  const { status, refresh } = useAuthStore();
  const [ch, setCh] = useState<ChallengeOut | null>(null);
  const [missing, setMissing] = useState(false);
  const [myPlans, setMyPlans] = useState<PlanSummary[]>([]);
  const [planId, setPlanId] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const scores = useSphereScores(ch);

  useEffect(() => {
    if (status === "unknown") void refresh();
  }, [status, refresh]);

  const load = useCallback(() => {
    challengesAPI
      .get(id)
      .then(setCh)
      .catch(() => setMissing(true));
  }, [id]);
  useEffect(load, [load]);

  useEffect(() => {
    if (status !== "signed-in") return;
    plansAPI
      .list({ mine: true })
      .then((r) => setMyPlans(r.data.filter((p) => p.visibility === "public")))
      .catch(() => setMyPlans([]));
  }, [status]);

  const entered = useMemo(
    () => new Set(ch?.entries.map((e) => e.planId)),
    [ch],
  );
  const eligible = myPlans.filter((p) => !entered.has(p.id));

  const act = async (fn: () => Promise<ChallengeOut>) => {
    setBusy(true);
    setError(null);
    try {
      setCh(await fn());
    } catch (err) {
      setError(err instanceof Error && err.message ? err.message : c.failed);
    } finally {
      setBusy(false);
    }
  };

  if (missing) {
    return (
      <div className="flex min-h-screen flex-col bg-gray-950">
        <Header />
        <p className="p-8 text-center text-gray-300">{t.detail.notFound}</p>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col bg-gray-950">
      <Header />
      <main className="flex-1 px-4 py-8 md:px-8">
        <div className="mx-auto max-w-4xl">
          <Link
            href="/challenges"
            className="mb-6 inline-flex items-center gap-2 text-sm text-gray-400 hover:text-white"
          >
            <ArrowLeft className="h-4 w-4" aria-hidden="true" />
            {c.title}
          </Link>
          {ch === null ? (
            <div className="h-60 animate-pulse rounded-xl bg-gray-900" />
          ) : (
            <>
              <header>
                <span
                  className={`rounded-full px-2 py-0.5 text-xs font-medium ${ch.isOpen ? "bg-primary-400/15 text-primary-200" : "bg-gray-800 text-gray-300"}`}
                >
                  {ch.isOpen ? c.open : c.closed}
                </span>
                <h1 className="mt-2 text-3xl font-semibold tracking-tight text-white">
                  {ch.title}
                </h1>
                <p className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-gray-400">
                  <span className="flex items-center gap-1.5">
                    {c.hostedBy.replace("{org}", ch.org.name)}
                    {ch.org.verified && <VerifiedBadge compact />}
                  </span>
                  <span className="flex items-center gap-1">
                    <Users className="h-4 w-4" aria-hidden="true" />
                    {c.people.replace(
                      "{n}",
                      ch.population.toLocaleString(lang),
                    )}
                  </span>
                  <span className="flex items-center gap-1">
                    <Clock className="h-4 w-4" aria-hidden="true" />
                    {(ch.isOpen ? c.closes : c.closedOn).replace(
                      "{date}",
                      new Date(ch.closesAt).toLocaleString(lang, {
                        dateStyle: "medium",
                        timeStyle: "short",
                      }),
                    )}
                  </span>
                </p>
                <p className="mt-4 max-w-prose whitespace-pre-line leading-relaxed text-gray-200">
                  {ch.brief}
                </p>
              </header>

              {ch.isOpen && (
                <section
                  className="mt-6 rounded-xl border border-gray-800 bg-gray-900 p-4"
                  aria-labelledby="enter-title"
                >
                  <h2
                    id="enter-title"
                    className="text-sm font-semibold text-gray-100"
                  >
                    {c.enter}
                  </h2>
                  {status !== "signed-in" ? (
                    <Link
                      href={`/login?next=${encodeURIComponent(`/challenges/${id}`)}`}
                      className="mt-2 inline-block text-sm font-medium text-primary-300 hover:underline"
                    >
                      {c.signIn}
                    </Link>
                  ) : eligible.length === 0 ? (
                    <p className="mt-2 text-sm text-gray-400">
                      {c.noPlans}{" "}
                      <Link
                        href={`/plan${ch.eventId ? `?event=${ch.eventId}` : ""}`}
                        className="font-medium text-primary-300 hover:underline"
                      >
                        {c.startPlan}
                      </Link>
                    </p>
                  ) : (
                    <div className="mt-2 flex flex-wrap items-end gap-2">
                      <div className="min-w-0 flex-1">
                        <label htmlFor="entry-plan" className="sr-only">
                          {c.enterPick}
                        </label>
                        <select
                          id="entry-plan"
                          className="field"
                          value={planId}
                          onChange={(e) => setPlanId(e.target.value)}
                        >
                          <option value="">{c.enterPick}</option>
                          {eligible.map((p) => (
                            <option key={p.id} value={p.id}>
                              {p.title}
                            </option>
                          ))}
                        </select>
                      </div>
                      <button
                        type="button"
                        className="btn-primary"
                        disabled={!planId || busy}
                        onClick={() =>
                          act(() => challengesAPI.enter(ch.id, planId))
                        }
                      >
                        {c.enterSubmit}
                      </button>
                    </div>
                  )}
                </section>
              )}
              {error && (
                <p role="alert" className="mt-3 text-sm text-ember-300">
                  {error}
                </p>
              )}

              <h2 className="mt-8 text-sm font-semibold text-gray-300">
                {c.entries.replace("{n}", String(ch.entries.length))}
              </h2>
              {ch.entries.length === 0 ? (
                <EmptyState className="mt-3" icon={LayoutGrid} title={c.noEntries} />
              ) : (
                <ol className="mt-3 space-y-3">
                  {ch.entries.map((e, i) => {
                    const met = scores[e.planId];
                    return (
                      <li
                        key={e.id}
                        className={`flex flex-wrap items-center gap-4 rounded-xl border p-4 ${e.selected ? "border-amber-400/50 bg-amber-400/5" : "border-gray-800 bg-gray-900"}`}
                      >
                        <span
                          className="w-6 text-center text-lg font-semibold tabular-nums text-gray-500"
                          aria-hidden="true"
                        >
                          {i + 1}
                        </span>
                        <div className="min-w-0 flex-1">
                          <div className="flex flex-wrap items-center gap-2">
                            <p className="font-medium text-white">
                              {e.planTitle}
                            </p>
                            {e.selected && (
                              <span className="flex items-center gap-1 rounded-full bg-amber-400/15 px-2 py-0.5 text-xs font-medium text-amber-200">
                                <Trophy
                                  className="h-3 w-3"
                                  aria-hidden="true"
                                />
                                {c.selected}
                              </span>
                            )}
                            {e.isMine && (
                              <span className="rounded-full bg-gray-800 px-2 py-0.5 text-xs text-gray-300">
                                {c.yours}
                              </span>
                            )}
                          </div>
                          <p className="mt-0.5 text-xs text-gray-400">
                            {t.plans.summary
                              .replace(
                                "{people}",
                                e.population.toLocaleString(lang),
                              )
                              .replace(
                                "{items}",
                                e.itemCount.toLocaleString(lang),
                              )
                              .replace("{v}", String(e.planVersion))}
                            {met !== undefined && (
                              <span
                                className={`ml-2 font-semibold ${met === 8 ? "text-primary-300" : met >= 6 ? "text-amber-300" : "text-ember-400"}`}
                              >
                                {c.sphere
                                  .replace("{met}", String(met))
                                  .replace("{total}", "8")}
                              </span>
                            )}
                          </p>
                        </div>
                        <Link
                          href={`/plan?id=${e.planId}`}
                          className="flex items-center gap-1 text-sm font-medium text-primary-300 hover:underline"
                        >
                          {c.view}
                          <ExternalLink
                            className="h-3.5 w-3.5"
                            aria-hidden="true"
                          />
                        </Link>
                        <button
                          type="button"
                          aria-pressed={e.votedByMe}
                          disabled={
                            busy ||
                            !ch.isOpen ||
                            e.isMine ||
                            status !== "signed-in"
                          }
                          onClick={() =>
                            act(() => challengesAPI.vote(e.id, !e.votedByMe))
                          }
                          className={`flex min-w-[5.5rem] items-center justify-center gap-1.5 rounded-lg border px-3 py-1.5 text-sm font-medium tabular-nums transition-colors disabled:cursor-not-allowed ${
                            e.votedByMe
                              ? "border-primary-400 bg-primary-400/15 text-primary-100"
                              : "border-gray-700 text-gray-200 hover:bg-gray-800 disabled:text-gray-500"
                          }`}
                        >
                          {e.votedByMe ? (
                            <Check className="h-4 w-4" aria-hidden="true" />
                          ) : (
                            <ThumbsUp className="h-4 w-4" aria-hidden="true" />
                          )}
                          <span className="sr-only">
                            {e.votedByMe ? c.voted : c.vote}:
                          </span>
                          {e.votes}
                        </button>
                        {ch.canManage && (
                          <button
                            type="button"
                            className="btn-ghost py-1.5 text-xs"
                            disabled={busy}
                            onClick={() =>
                              act(() =>
                                challengesAPI.select(
                                  ch.id,
                                  e.selected ? null : e.id,
                                ),
                              )
                            }
                          >
                            <Trophy
                              className="h-3.5 w-3.5"
                              aria-hidden="true"
                            />
                            {e.selected ? c.unselect : c.select}
                          </button>
                        )}
                      </li>
                    );
                  })}
                </ol>
              )}
            </>
          )}
        </div>
      </main>
    </div>
  );
}
