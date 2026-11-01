"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { Check, GitFork, Link2, Save } from "lucide-react";
import {
  communityAPI,
  plansAPI,
  type Need,
  type PlanOut,
} from "@/lib/api/community";
import { useTranslation } from "@/lib/i18n/useTranslation";
import { toWire, type PlanItem } from "@/lib/sphere";
import { approvedOrgs, useAuthStore } from "@/store/authStore";

interface PlanSaveBarProps {
  plan: PlanOut | null;
  items: PlanItem[];
  population: number;
  eventId: string | null;
  defaultTitle: string;
  /** A plan was created, saved, forked or a version picked */
  onPlan: (plan: PlanOut) => void;
}

/**
 * Save the layout as a plan (each save is a new version), switch versions,
 * fork someone else's plan, and attach a public plan to one of the
 * organisation's needs.
 */
export function PlanSaveBar({
  plan,
  items,
  population,
  eventId,
  defaultTitle,
  onPlan,
}: PlanSaveBarProps) {
  const { t } = useTranslation();
  const p = t.plans;
  const { me, status, refresh } = useAuthStore();
  const [title, setTitle] = useState(plan?.title ?? defaultTitle);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<{ text: string; ok: boolean } | null>(
    null,
  );
  const [needs, setNeeds] = useState<Need[] | null>(null);
  const [needId, setNeedId] = useState("");
  const orgs = useMemo(() => approvedOrgs(me), [me]);
  const mine = plan === null || plan.isMine;

  useEffect(() => {
    if (status === "unknown") void refresh();
  }, [status, refresh]);

  useEffect(() => {
    if (plan) setTitle(plan.title);
  }, [plan]);

  // Needs this user can attach a plan to: their organisations' open needs
  useEffect(() => {
    if (!plan?.isMine || plan.visibility !== "public" || orgs.length === 0)
      return;
    communityAPI
      .needs({ eventId: eventId ?? undefined, status: "open", limit: 100 })
      .then((r) => setNeeds(r.data.filter((n) => n.canEdit)))
      .catch(() => setNeeds([]));
  }, [plan?.id, plan?.isMine, plan?.visibility, orgs.length, eventId]);

  const run = async (fn: () => Promise<void>) => {
    setBusy(true);
    setMessage(null);
    try {
      await fn();
    } catch (err) {
      setMessage({
        text: err instanceof Error && err.message ? err.message : p.saveFailed,
        ok: false,
      });
    } finally {
      setBusy(false);
    }
  };

  const save = () =>
    run(async () => {
      const content = {
        population,
        items: toWire(items),
        note: note.trim() || null,
      };
      const saved = plan
        ? await plansAPI.saveVersion(plan.id, content)
        : await plansAPI.create({
            ...content,
            title: title.trim() || p.untitled,
            event_id: eventId,
            visibility: "public",
          });
      if (plan && title.trim() && title.trim() !== plan.title)
        await plansAPI.update(plan.id, { title: title.trim() });
      setNote("");
      onPlan({ ...saved, title: title.trim() || saved.title });
      setMessage({
        text: p.saved.replace("{n}", String(saved.version)),
        ok: true,
      });
    });

  if (status !== "signed-in") {
    return (
      <div className="mt-4 rounded-lg border border-gray-800 p-3 text-sm">
        <Link
          href={`/login?next=${encodeURIComponent("/plan" + (eventId ? `?event=${eventId}` : ""))}`}
          className="font-medium text-primary-300 hover:underline"
        >
          {p.signInToSave}
        </Link>
      </div>
    );
  }

  return (
    <div className="mt-4 space-y-3 rounded-lg border border-gray-800 p-3">
      {plan && plan.forkedFromVersion != null && (
        <p className="flex items-center gap-1.5 text-xs text-gray-400">
          <GitFork className="h-3.5 w-3.5" aria-hidden="true" />
          {p.forkedFrom.replace("{n}", String(plan.forkedFromVersion))}
        </p>
      )}

      <div>
        <label htmlFor="plan-title" className="field-label">
          {p.titleField}
        </label>
        <input
          id="plan-title"
          className="field"
          maxLength={200}
          value={title}
          readOnly={!mine}
          onChange={(e) => setTitle(e.target.value)}
        />
      </div>

      {plan && plan.versions.length > 1 && (
        <div>
          <label htmlFor="plan-version" className="field-label">
            {p.version}
          </label>
          <select
            id="plan-version"
            className="field"
            value={plan.version}
            onChange={(e) =>
              run(async () => {
                onPlan(await plansAPI.get(plan.id, Number(e.target.value)));
              })
            }
          >
            {plan.versions.map((v) => (
              <option key={v.number} value={v.number}>
                v{v.number}
                {v.number === plan.latestVersion ? ` (${p.latest})` : ""}
                {v.note ? ` — ${v.note}` : ""}
              </option>
            ))}
          </select>
        </div>
      )}

      {mine ? (
        <>
          <div>
            <label htmlFor="plan-note" className="field-label">
              {p.note}
            </label>
            <input
              id="plan-note"
              className="field"
              maxLength={1000}
              value={note}
              onChange={(e) => setNote(e.target.value)}
            />
          </div>
          <button
            type="button"
            className="btn-primary w-full"
            disabled={busy || items.length === 0}
            onClick={save}
          >
            <Save className="h-4 w-4" aria-hidden="true" />
            {plan
              ? p.saveVersion.replace("{n}", String(plan.latestVersion + 1))
              : p.save}
          </button>
        </>
      ) : (
        <>
          <p className="text-xs text-gray-400">{p.readOnly}</p>
          <button
            type="button"
            className="btn-primary w-full"
            disabled={busy}
            onClick={() =>
              run(async () => {
                onPlan(await plansAPI.fork(plan!.id, plan!.version));
                setMessage({ text: p.forked, ok: true });
              })
            }
          >
            <GitFork className="h-4 w-4" aria-hidden="true" />
            {p.fork}
          </button>
        </>
      )}

      {plan?.isMine && plan.visibility === "public" && needs !== null && (
        <div className="border-t border-gray-800 pt-3">
          {needs.length === 0 ? (
            <p className="text-xs text-gray-400">{p.noNeeds}</p>
          ) : (
            <div className="flex items-end gap-2">
              <div className="min-w-0 flex-1">
                <label htmlFor="plan-need" className="field-label">
                  {p.attach}
                </label>
                <select
                  id="plan-need"
                  className="field"
                  value={needId}
                  onChange={(e) => setNeedId(e.target.value)}
                >
                  <option value="">{p.attachPick}</option>
                  {needs.map((n) => (
                    <option key={n.id} value={n.id}>
                      {n.title}
                      {n.planId === plan.id ? " ✓" : ""}
                    </option>
                  ))}
                </select>
              </div>
              <button
                type="button"
                className="btn-ghost shrink-0"
                disabled={busy || !needId}
                aria-label={p.attach}
                title={p.attach}
                onClick={() =>
                  run(async () => {
                    const updated = await plansAPI.attachToNeed(
                      needId,
                      plan.id,
                    );
                    setNeeds(
                      (list) =>
                        list?.map((n) => (n.id === updated.id ? updated : n)) ??
                        null,
                    );
                    setMessage({ text: p.attached, ok: true });
                  })
                }
              >
                <Link2 className="h-4 w-4" aria-hidden="true" />
              </button>
            </div>
          )}
        </div>
      )}

      {message && (
        <p
          role={message.ok ? "status" : "alert"}
          className={`flex items-center gap-1.5 text-xs ${message.ok ? "text-primary-300" : "text-ember-300"}`}
        >
          {message.ok && <Check className="h-3.5 w-3.5" aria-hidden="true" />}
          {message.text}
        </p>
      )}
    </div>
  );
}
