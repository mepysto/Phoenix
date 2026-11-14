"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { HandHeart, LayoutGrid, Megaphone, Plus, Trophy } from "lucide-react";
import { EmptyState } from "@/components/ui/States";
import { CategoryIcon } from "@/components/connect/CategoryIcon";
import { VerifiedBadge } from "@/components/connect/VerifiedBadge";
import {
  communityAPI,
  type ChallengeSummary,
  type Disclosure,
  type Need,
  type PlanSummary,
} from "@/lib/api/community";
import { useTranslation } from "@/lib/i18n/useTranslation";
import { formatDate, formatWhen } from "@/lib/format";
import { approvedOrgs, useAuthStore } from "@/store/authStore";

const PRIORITY_DOT: Record<string, string> = {
  critical: "bg-ember-500",
  high: "bg-amber-400",
  medium: "bg-primary-400",
  low: "bg-gray-500",
};

const CARD = "rounded-xl border border-gray-700/80 bg-gray-900 p-5";
const ROW = "rounded-lg bg-gray-950/60 px-3 py-2.5";

function Loading({ h = "h-16" }: { h?: string }) {
  return <div className={`${h} animate-pulse rounded-lg bg-gray-800`} />;
}

/** Needs for this disaster; when there are none, how needs and help meet (UX plan 5.3) */
export function EventNeeds({ eventId, needs }: { eventId: string; needs: Need[] | null }) {
  const { t, lang } = useTranslation();
  const me = useAuthStore((s) => s.me);
  const canPost = approvedOrgs(me).length > 0;
  const actions = (
    <div className="flex flex-wrap gap-2">
      <Link href={`/connect?event=${eventId}`} className="btn-primary">
        <HandHeart className="h-4 w-4" aria-hidden="true" />
        {t.connect.offerHelp}
      </Link>
      {canPost && (
        <Link href="/connect/mine" className="btn-ghost">
          <Plus className="h-4 w-4" aria-hidden="true" />
          {t.connect.postNeed}
        </Link>
      )}
    </div>
  );

  if (needs === null) return <Loading h="h-24" />;
  if (needs.length === 0) {
    return (
      <section className={CARD} aria-labelledby="event-needs-title">
        <h2 id="event-needs-title" className="text-lg font-semibold text-white">
          {t.connect.eventNeeds.none}
        </h2>
        <ol className="mt-4 space-y-3">
          {[t.ux.helpStep1, t.ux.helpStep2, t.ux.helpStep3].map((step, i) => (
            <li key={step} className="flex gap-3 text-sm text-gray-200">
              <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary-400/15 text-xs font-semibold text-primary-200">
                {i + 1}
              </span>
              {step}
            </li>
          ))}
        </ol>
        <div className="mt-5">{actions}</div>
      </section>
    );
  }
  return (
    <section className={CARD} aria-labelledby="event-needs-title">
      <div className="mb-4 flex items-center justify-between gap-2">
        <h2 id="event-needs-title" className="text-lg font-semibold text-white">
          {t.connect.eventNeeds.title}
        </h2>
        <Link href={`/connect?event=${eventId}`} className="text-sm font-medium text-primary-300 hover:underline">
          {t.connect.eventNeeds.all}
        </Link>
      </div>
      <ul className="space-y-2">
        {needs.map((n) => (
          <li key={n.id} className={`flex items-start gap-3 ${ROW}`}>
            <span aria-hidden="true" className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${PRIORITY_DOT[n.priority]}`} />
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium text-gray-100">{n.title}</p>
              <p className="text-sm text-gray-400">
                {n.org.name} · {t.connect.priority[n.priority]}
                {n.quantity ? ` · ${n.quantity.toLocaleString(lang)} ${n.unit ?? ""}` : ""}
              </p>
            </div>
            <span className="flex gap-1 text-gray-400">
              {n.categories.slice(0, 3).map((c) => (
                <CategoryIcon key={c} category={c} className="h-4 w-4" />
              ))}
            </span>
          </li>
        ))}
      </ul>
      <div className="mt-5">{actions}</div>
    </section>
  );
}

/** Site plans and design challenges for this disaster */
export function EventDesign({
  eventId,
  plans,
  challenges,
}: {
  eventId: string;
  plans: PlanSummary[] | null;
  challenges: ChallengeSummary[] | null;
}) {
  const { t, lang } = useTranslation();
  const start = (
    <Link href={`/plan?event=${eventId}`} className="btn-primary">
      <LayoutGrid className="h-4 w-4" aria-hidden="true" />
      {t.ux.navPlan}
    </Link>
  );
  return (
    <div className="space-y-4">
      <section className={CARD} aria-labelledby="plans-title">
        <div className="mb-4 flex items-center justify-between gap-2">
          <h2 id="plans-title" className="text-lg font-semibold text-white">
            {t.plans.listTitle}
          </h2>
          {plans && plans.length > 0 && start}
        </div>
        {plans === null ? (
          <Loading />
        ) : plans.length === 0 ? (
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-sm text-gray-300">{t.ux.designEmpty}</p>
            {start}
          </div>
        ) : (
          <ul className="space-y-2">
            {plans.map((pl) => (
              <li key={pl.id}>
                <Link href={`/plan?id=${pl.id}`} className={`block ${ROW} hover:bg-gray-800`}>
                  <p className="text-sm font-medium text-gray-100">{pl.title}</p>
                  <p className="text-sm text-gray-400">
                    {t.plans.summary
                      .replace("{people}", pl.population.toLocaleString(lang))
                      .replace("{items}", pl.itemCount.toLocaleString(lang))
                      .replace("{v}", String(pl.latestVersion))}
                    {" · "}
                    <time dateTime={pl.updatedAt} title={formatDate(pl.updatedAt, lang)}>
                      {formatWhen(pl.updatedAt, lang)}
                    </time>
                  </p>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>

      {challenges && challenges.length > 0 && (
        <section className={CARD} aria-labelledby="event-challenges-title">
          <h2 id="event-challenges-title" className="mb-4 flex items-center gap-2 text-lg font-semibold text-white">
            <Trophy className="h-5 w-5 text-primary-400" aria-hidden="true" />
            {t.ux.navChallenges}
          </h2>
          <ul className="space-y-2">
            {challenges.map((ch) => (
              <li key={ch.id}>
                <Link href={`/challenges/${ch.id}`} className={`block ${ROW} hover:bg-gray-800`}>
                  <p className="text-sm font-medium text-gray-100">{ch.title}</p>
                  <p className="text-sm text-gray-400">
                    {(ch.isOpen ? t.challenges.closes : t.challenges.closedOn).replace(
                      "{date}",
                      formatDate(ch.closesAt, lang),
                    )}
                  </p>
                </Link>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}

/** Progress updates from organisations, newest first; members of an approved organisation can post */
export function EventUpdates({
  eventId,
  updates,
  onPublished,
}: {
  eventId: string;
  updates: Disclosure[] | null;
  onPublished: (update: Disclosure) => void;
}) {
  const { t, lang } = useTranslation();
  const me = useAuthStore((s) => s.me);
  const orgs = useMemo(() => approvedOrgs(me), [me]);
  const [form, setForm] = useState({ orgId: "", title: "", body: "" });
  const [error, setError] = useState<string | null>(null);

  const publish = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      const d = await communityAPI.publishDisclosure(eventId, {
        org_id: form.orgId || orgs[0]!.id,
        title: form.title,
        body: form.body,
      });
      onPublished(d);
      setForm({ orgId: "", title: "", body: "" });
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  return (
    <section className={CARD} aria-labelledby="updates-title">
      <h2 id="updates-title" className="mb-4 flex items-center gap-2 text-lg font-semibold text-white">
        <Megaphone className="h-5 w-5 text-primary-400" aria-hidden="true" />
        {t.connect.disclosures.title}
      </h2>
      {updates === null ? (
        <Loading />
      ) : updates.length === 0 ? (
        <EmptyState compact icon={Megaphone} title={t.connect.disclosures.none} />
      ) : (
        <ol className="relative space-y-5 border-s border-gray-700 ps-5">
          {updates.map((d) => (
            <li key={d.id} className="relative">
              <span
                aria-hidden="true"
                className="absolute -start-[25px] top-1.5 h-2 w-2 rounded-full bg-primary-400 ring-4 ring-gray-900"
              />
              <p className="text-sm text-gray-400">
                <time dateTime={d.createdAt}>{formatDate(d.createdAt, lang)}</time>
                {" · "}
                {d.org.name}
                {d.org.verified && (
                  <>
                    {" "}
                    <VerifiedBadge compact />
                  </>
                )}
              </p>
              <p className="mt-0.5 font-medium text-gray-100">{d.title}</p>
              <p className="mt-1 whitespace-pre-line text-sm text-gray-300">{d.body}</p>
            </li>
          ))}
        </ol>
      )}

      {orgs.length > 0 && (
        <form onSubmit={publish} className="mt-6 space-y-3 border-t border-gray-800 pt-5">
          <h3 className="text-sm font-semibold text-gray-200">{t.connect.disclosures.publish}</h3>
          {orgs.length > 1 && (
            <select
              aria-label={t.connect.form.org}
              className="field"
              value={form.orgId}
              onChange={(e) => setForm((f) => ({ ...f, orgId: e.target.value }))}
            >
              {orgs.map((o) => (
                <option key={o.id} value={o.id}>
                  {o.name}
                </option>
              ))}
            </select>
          )}
          <div>
            <label htmlFor="d-title" className="field-label">
              {t.connect.disclosures.titleField}
            </label>
            <input
              id="d-title"
              required
              minLength={3}
              maxLength={200}
              className="field"
              value={form.title}
              onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
            />
          </div>
          <div>
            <label htmlFor="d-body" className="field-label">
              {t.connect.disclosures.body}
            </label>
            <textarea
              id="d-body"
              required
              minLength={10}
              rows={3}
              className="field"
              value={form.body}
              onChange={(e) => setForm((f) => ({ ...f, body: e.target.value }))}
            />
          </div>
          {error && (
            <p role="alert" className="text-sm text-ember-300">
              {error}
            </p>
          )}
          <button type="submit" className="btn-primary">
            {t.connect.disclosures.submit}
          </button>
        </form>
      )}
    </section>
  );
}
