"use client";

import { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Plus, Trophy } from "lucide-react";
import { EmptyState } from "@/components/ui/States";
import { ChallengeCard } from "@/components/challenges/ChallengeCard";
import { Header } from "@/components/layout/Header";
import { SlideOver } from "@/components/connect/SlideOver";
import { eventsAPI } from "@/lib/api/client";
import { challengesAPI, type ChallengeSummary } from "@/lib/api/community";
import { useTranslation } from "@/lib/i18n/useTranslation";
import { approvedOrgs, useAuthStore } from "@/store/authStore";

function CreateForm({
  eventId,
  onDone,
}: {
  eventId?: string;
  onDone: (id: string) => void;
}) {
  const { t } = useTranslation();
  const c = t.challenges;
  const me = useAuthStore((s) => s.me);
  const orgs = useMemo(() => approvedOrgs(me), [me]);
  const [events, setEvents] = useState<{ id: string; title: string }[]>([]);
  const [form, setForm] = useState({
    orgId: orgs[0]?.id ?? "",
    eventId: eventId ?? "",
    title: "",
    brief: "",
    population: "1000",
    closesAt: new Date(Date.now() + 14 * 86_400_000).toISOString().slice(0, 10),
  });
  const [error, setError] = useState<string | null>(null);
  const set = (k: keyof typeof form, v: string) =>
    setForm((f) => ({ ...f, [k]: v }));

  useEffect(() => {
    eventsAPI
      .list({ isActive: true }, 200)
      .then((r) => setEvents(r.data.map((e) => ({ id: e.id, title: e.title }))))
      .catch(() => setEvents([]));
  }, []);

  if (orgs.length === 0)
    return <p className="text-sm text-gray-300">{c.needOrg}</p>;
  return (
    <form
      className="space-y-4"
      onSubmit={async (e) => {
        e.preventDefault();
        setError(null);
        try {
          const created = await challengesAPI.create({
            org_id: form.orgId,
            event_id: form.eventId || null,
            title: form.title,
            brief: form.brief,
            population: Number(form.population),
            // End of the chosen day, UTC
            closes_at: `${form.closesAt}T23:59:00Z`,
          });
          onDone(created.id);
        } catch (err) {
          setError(err instanceof Error ? err.message : c.failed);
        }
      }}
    >
      {orgs.length > 1 && (
        <div>
          <label htmlFor="ch-org" className="field-label">
            {c.org}
          </label>
          <select
            id="ch-org"
            className="field"
            value={form.orgId}
            onChange={(e) => set("orgId", e.target.value)}
          >
            {orgs.map((o) => (
              <option key={o.id} value={o.id}>
                {o.name}
              </option>
            ))}
          </select>
        </div>
      )}
      <div>
        <label htmlFor="ch-event" className="field-label">
          {c.event}
        </label>
        <select
          id="ch-event"
          className="field"
          value={form.eventId}
          onChange={(e) => set("eventId", e.target.value)}
        >
          <option value="">{c.noEvent}</option>
          {events.map((ev) => (
            <option key={ev.id} value={ev.id}>
              {ev.title}
            </option>
          ))}
        </select>
      </div>
      <div>
        <label htmlFor="ch-title" className="field-label">
          {c.titleField}
        </label>
        <input
          id="ch-title"
          required
          minLength={3}
          maxLength={200}
          className="field"
          value={form.title}
          onChange={(e) => set("title", e.target.value)}
        />
      </div>
      <div>
        <label htmlFor="ch-brief" className="field-label">
          {c.brief}
        </label>
        <textarea
          id="ch-brief"
          required
          minLength={10}
          maxLength={4000}
          rows={5}
          className="field"
          value={form.brief}
          onChange={(e) => set("brief", e.target.value)}
        />
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label htmlFor="ch-pop" className="field-label">
            {c.population}
          </label>
          <input
            id="ch-pop"
            type="number"
            min={1}
            max={1000000}
            required
            className="field"
            value={form.population}
            onChange={(e) => set("population", e.target.value)}
          />
        </div>
        <div>
          <label htmlFor="ch-close" className="field-label">
            {c.closesAt}
          </label>
          <input
            id="ch-close"
            type="date"
            required
            className="field"
            value={form.closesAt}
            min={new Date().toISOString().slice(0, 10)}
            onChange={(e) => set("closesAt", e.target.value)}
          />
        </div>
      </div>
      {error && (
        <p role="alert" className="text-sm text-ember-300">
          {error}
        </p>
      )}
      <button type="submit" className="btn-primary w-full">
        {c.submit}
      </button>
    </form>
  );
}

function ChallengesContent() {
  const { t } = useTranslation();
  const c = t.challenges;
  const eventId = useSearchParams().get("event") ?? undefined;
  const { status, refresh } = useAuthStore();
  const [list, setList] = useState<ChallengeSummary[] | null>(null);
  const [panel, setPanel] = useState(false);

  useEffect(() => {
    if (status === "unknown") void refresh();
  }, [status, refresh]);

  const load = useCallback(() => {
    challengesAPI
      .list(eventId)
      .then((r) => setList(r.data))
      .catch(() => setList([]));
  }, [eventId]);
  useEffect(load, [load]);

  return (
    <main className="flex-1 px-4 py-8 md:px-8">
      <div className="mx-auto max-w-5xl">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div className="max-w-2xl">
            <h1 className="text-3xl font-semibold tracking-tight text-white">
              {c.title}
            </h1>
            <p className="mt-2 text-gray-300">{c.intro}</p>
          </div>
          {status === "signed-in" ? (
            <button
              type="button"
              className="btn-primary"
              onClick={() => setPanel(true)}
            >
              <Plus className="h-4 w-4" aria-hidden="true" />
              {c.create}
            </button>
          ) : (
            <Link
              href={`/login?next=${encodeURIComponent("/challenges")}`}
              className="btn-ghost"
            >
              {c.signIn}
            </Link>
          )}
        </div>
        <div className="mt-8 grid gap-3 md:grid-cols-2">
          {list === null ? (
            [0, 1].map((i) => (
              <div
                key={i}
                className="h-40 animate-pulse rounded-xl bg-gray-900"
              />
            ))
          ) : list.length === 0 ? (
            <EmptyState
              className="md:col-span-2"
              icon={Trophy}
              title={c.none}
              action={
                status === "signed-in" ? (
                  <button
                    type="button"
                    className="btn-primary"
                    onClick={() => setPanel(true)}
                  >
                    <Plus className="h-4 w-4" aria-hidden="true" />
                    {c.create}
                  </button>
                ) : undefined
              }
            />
          ) : (
            list.map((ch) => <ChallengeCard key={ch.id} ch={ch} />)
          )}
        </div>
      </div>
      <SlideOver
        open={panel}
        title={c.create}
        onClose={() => setPanel(false)}
        closeLabel={t.common.close}
      >
        <CreateForm
          eventId={eventId}
          onDone={(id) => {
            setPanel(false);
            window.location.href = `/challenges/${id}`;
          }}
        />
      </SlideOver>
    </main>
  );
}

export default function ChallengesPage() {
  return (
    <div className="flex min-h-screen flex-col bg-gray-950">
      <Header />
      <Suspense>
        <ChallengesContent />
      </Suspense>
    </div>
  );
}
