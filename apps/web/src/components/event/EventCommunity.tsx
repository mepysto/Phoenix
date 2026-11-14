"use client";

import { EmptyState } from "@/components/ui/States";
import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { HandHeart, LayoutGrid, Megaphone } from "lucide-react";
import { CategoryIcon } from "@/components/connect/CategoryIcon";
import { VerifiedBadge } from "@/components/connect/VerifiedBadge";
import {
  communityAPI,
  plansAPI,
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

/** Needs posted for this event, and progress updates from organisations. */
export function EventCommunity({ eventId }: { eventId: string }) {
  const { t, lang } = useTranslation();
  const me = useAuthStore((s) => s.me);
  const orgs = useMemo(() => approvedOrgs(me), [me]);
  const [needs, setNeeds] = useState<Need[] | null>(null);
  const [updates, setUpdates] = useState<Disclosure[] | null>(null);
  const [plans, setPlans] = useState<PlanSummary[] | null>(null);
  const [form, setForm] = useState({ orgId: "", title: "", body: "" });
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    communityAPI
      .needs({ eventId, status: "open", limit: 5 })
      .then((r) => setNeeds(r.data))
      .catch(() => setNeeds([]));
    plansAPI
      .list({ eventId })
      .then((r) => setPlans(r.data))
      .catch(() => setPlans([]));
    communityAPI
      .disclosures(eventId)
      .then((r) => setUpdates(r.data))
      .catch(() => setUpdates([]));
  }, [eventId]);

  const publish = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      const d = await communityAPI.publishDisclosure(eventId, {
        org_id: form.orgId || orgs[0]!.id,
        title: form.title,
        body: form.body,
      });
      setUpdates((u) => [d, ...(u ?? [])]);
      setForm({ orgId: "", title: "", body: "" });
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  return (
    <>
      <section
        className="rounded-xl border border-gray-700/80 bg-gray-900 p-6"
        aria-labelledby="event-needs-title"
      >
        <div className="mb-4 flex items-center justify-between gap-2">
          <h2
            id="event-needs-title"
            className="flex items-center gap-2 text-lg font-semibold text-white"
          >
            <HandHeart
              className="h-5 w-5 text-primary-400"
              aria-hidden="true"
            />
            {t.connect.eventNeeds.title}
          </h2>
          <Link
            href={`/connect?event=${eventId}`}
            className="shrink-0 whitespace-nowrap text-sm font-medium text-primary-300 hover:underline"
          >
            {t.connect.eventNeeds.all}
          </Link>
        </div>
        {needs === null ? (
          <div className="h-20 animate-pulse rounded-lg bg-gray-800" />
        ) : needs.length === 0 ? (
          <EmptyState
            compact
            icon={HandHeart}
            title={t.connect.eventNeeds.none}
          />
        ) : (
          <ul className="space-y-2">
            {needs.map((n) => (
              <li
                key={n.id}
                className="flex items-start gap-3 rounded-lg bg-gray-950/60 px-3 py-2.5"
              >
                <span
                  aria-hidden="true"
                  className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${PRIORITY_DOT[n.priority]}`}
                />
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-gray-100">{n.title}</p>
                  <p className="text-xs text-gray-400">
                    {n.org.name} · {t.connect.priority[n.priority]}
                    {n.quantity
                      ? ` · ${n.quantity.toLocaleString(lang)} ${n.unit ?? ""}`
                      : ""}
                  </p>
                </div>
                <span className="flex gap-1 text-gray-400">
                  {n.categories.slice(0, 3).map((c) => (
                    <CategoryIcon
                      key={c}
                      category={c}
                      className="h-3.5 w-3.5"
                    />
                  ))}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section
        className="rounded-xl border border-gray-700/80 bg-gray-900 p-6"
        aria-labelledby="plans-title"
      >
        <div className="mb-4 flex items-center justify-between gap-2">
          <h2
            id="plans-title"
            className="flex items-center gap-2 text-lg font-semibold text-white"
          >
            <LayoutGrid
              className="h-5 w-5 text-primary-400"
              aria-hidden="true"
            />
            {t.plans.listTitle}
          </h2>
          <Link
            href={`/plan?event=${eventId}`}
            className="shrink-0 whitespace-nowrap text-sm font-medium text-primary-300 hover:underline"
          >
            {t.plans.start}
          </Link>
        </div>
        {plans === null ? (
          <div className="h-12 animate-pulse rounded-lg bg-gray-800" />
        ) : plans.length === 0 ? (
          <EmptyState compact icon={LayoutGrid} title={t.plans.none} />
        ) : (
          <ul className="space-y-2">
            {plans.slice(0, 6).map((pl) => (
              <li key={pl.id}>
                <Link
                  href={`/plan?id=${pl.id}`}
                  className="block rounded-lg bg-gray-950/60 px-3 py-2.5 hover:bg-gray-800"
                >
                  <p className="text-sm font-medium text-gray-100">
                    {pl.title}
                  </p>
                  <p className="text-xs text-gray-400">
                    {t.plans.summary
                      .replace("{people}", pl.population.toLocaleString(lang))
                      .replace("{items}", pl.itemCount.toLocaleString(lang))
                      .replace("{v}", String(pl.latestVersion))}
                    {" · "}
                    <time
                      dateTime={pl.updatedAt}
                      title={formatDate(pl.updatedAt, lang)}
                    >
                      {formatWhen(pl.updatedAt, lang)}
                    </time>
                  </p>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section
        className="rounded-xl border border-gray-700/80 bg-gray-900 p-6"
        aria-labelledby="updates-title"
      >
        <h2
          id="updates-title"
          className="mb-4 flex items-center gap-2 text-lg font-semibold text-white"
        >
          <Megaphone className="h-5 w-5 text-primary-400" aria-hidden="true" />
          {t.connect.disclosures.title}
        </h2>
        {updates === null ? (
          <div className="h-16 animate-pulse rounded-lg bg-gray-800" />
        ) : updates.length === 0 ? (
          <EmptyState
            compact
            icon={Megaphone}
            title={t.connect.disclosures.none}
          />
        ) : (
          <ol className="relative space-y-5 border-l border-gray-700 pl-5">
            {updates.map((d) => (
              <li key={d.id} className="relative">
                <span
                  aria-hidden="true"
                  className="absolute -left-[25px] top-1.5 h-2 w-2 rounded-full bg-primary-400 ring-4 ring-gray-900"
                />
                <p className="text-xs text-gray-400">
                  <time dateTime={d.createdAt}>
                    {formatDate(d.createdAt, lang)}
                  </time>
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
                <p className="mt-1 whitespace-pre-line text-sm text-gray-300">
                  {d.body}
                </p>
              </li>
            ))}
          </ol>
        )}

        {orgs.length > 0 && (
          <form
            onSubmit={publish}
            className="mt-6 space-y-3 border-t border-gray-800 pt-5"
          >
            <h3 className="text-sm font-semibold text-gray-200">
              {t.connect.disclosures.publish}
            </h3>
            {orgs.length > 1 && (
              <select
                aria-label={t.connect.form.org}
                className="field"
                value={form.orgId}
                onChange={(e) =>
                  setForm((f) => ({ ...f, orgId: e.target.value }))
                }
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
                onChange={(e) =>
                  setForm((f) => ({ ...f, title: e.target.value }))
                }
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
                onChange={(e) =>
                  setForm((f) => ({ ...f, body: e.target.value }))
                }
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
    </>
  );
}
