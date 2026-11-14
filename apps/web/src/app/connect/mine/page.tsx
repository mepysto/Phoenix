"use client";

import { EmptyState } from "@/components/ui/States";
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  Building2,
  Check,
  CircleDashed,
  Handshake,
  Mail,
  X,
} from "lucide-react";
import { Header } from "@/components/layout/Header";
import { ContributionsCard } from "@/components/connect/ContributionsCard";
import { VerifiedBadge } from "@/components/connect/VerifiedBadge";
import {
  communityAPI,
  type Connect,
  type Offer,
  type OrgType,
} from "@/lib/api/community";
import { useTranslation } from "@/lib/i18n/useTranslation";
import { useAuthStore } from "@/store/authStore";

const ORG_TYPES: OrgType[] = [
  "local_partner",
  "international_ngo",
  "un",
  "government",
  "other",
];

function StatusPill({
  status,
}: {
  status: "pending" | "approved" | "rejected";
}) {
  const { t } = useTranslation();
  const style = {
    pending: "bg-amber-400/15 text-amber-200",
    approved: "bg-primary-400/15 text-primary-200",
    rejected: "bg-ember-500/15 text-ember-300",
  }[status];
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${style}`}>
      {t.connect.mine[status]}
    </span>
  );
}

function ConnectRow({ c, onChange }: { c: Connect; onChange: () => void }) {
  const { t } = useTranslation();
  const m = t.connect.mine;
  const [busy, setBusy] = useState(false);
  const mineApproved = c.mySides.every((s) =>
    s === "need" ? c.needApproved : c.offerApproved,
  );
  const label =
    c.status === "approved"
      ? m.connected
      : c.status === "rejected"
        ? m.declined
        : c.status === "canceled"
          ? m.canceled
          : mineApproved
            ? m.waitingThem
            : m.waitingYou;
  const act = async (fn: (id: string) => Promise<unknown>) => {
    setBusy(true);
    try {
      await fn(c.id);
      onChange();
    } finally {
      setBusy(false);
    }
  };

  return (
    <li className="rounded-xl border border-gray-700/80 bg-gray-900 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-sm text-gray-400">{c.need.org.name}</p>
          <p className="font-medium text-white">{c.need.title}</p>
          <p className="mt-1 flex items-center gap-1.5 text-sm text-gray-300">
            <Handshake
              className="h-4 w-4 text-primary-400"
              aria-hidden="true"
            />
            {c.offer.title}
          </p>
        </div>
        <span
          className={`flex items-center gap-1.5 text-xs font-medium ${
            c.status === "approved"
              ? "text-primary-300"
              : c.status === "pending"
                ? "text-amber-200"
                : "text-gray-400"
          }`}
        >
          {c.status === "approved" ? (
            <Check className="h-3.5 w-3.5" aria-hidden="true" />
          ) : (
            <CircleDashed className="h-3.5 w-3.5" aria-hidden="true" />
          )}
          {label}
        </span>
      </div>
      {/* Two-sided approval, shown as two steps */}
      <ol className="mt-3 flex gap-2 text-xs" aria-label={label}>
        {(["need", "offer"] as const).map((side) => {
          const ok = side === "need" ? c.needApproved : c.offerApproved;
          return (
            <li
              key={side}
              className={`flex-1 rounded-md border px-2 py-1 ${ok ? "border-primary-500/50 text-primary-200" : "border-gray-700 text-gray-400"}`}
            >
              {side === "need" ? t.connect.tabNeeds : t.connect.tabOffers}{" "}
              {ok ? "✓" : "…"}
            </li>
          );
        })}
      </ol>
      {c.counterpartEmail && (
        <a
          href={`mailto:${c.counterpartEmail}`}
          className="mt-3 flex items-center gap-2 text-sm font-medium text-primary-300 hover:underline"
        >
          <Mail className="h-4 w-4" aria-hidden="true" />
          {m.contactAt.replace("{email}", c.counterpartEmail)}
        </a>
      )}
      {c.status === "pending" && (
        <div className="mt-3 flex gap-2">
          {!mineApproved && (
            <button
              type="button"
              className="btn-primary py-1.5 text-xs"
              disabled={busy}
              onClick={() => act(communityAPI.approve)}
            >
              <Check className="h-3.5 w-3.5" aria-hidden="true" />
              {m.approve}
            </button>
          )}
          <button
            type="button"
            className="btn-ghost py-1.5 text-xs"
            disabled={busy}
            onClick={() => act(communityAPI.decline)}
          >
            <X className="h-3.5 w-3.5" aria-hidden="true" />
            {m.decline}
          </button>
        </div>
      )}
    </li>
  );
}

function ApplyOrg({ onDone }: { onDone: () => void }) {
  const { t } = useTranslation();
  const m = t.connect.mine;
  const [name, setName] = useState("");
  const [orgType, setOrgType] = useState<OrgType>("local_partner");
  const [email, setEmail] = useState("");
  const [website, setWebsite] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      await communityAPI.applyOrg({
        name,
        org_type: orgType,
        primary_email: email,
        website: website || null,
      });
      setDone(true);
      setName("");
      setEmail("");
      setWebsite("");
      onDone();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  return (
    <form
      onSubmit={submit}
      className="space-y-3 rounded-xl border border-gray-700/80 bg-gray-900 p-5"
    >
      <h3 className="font-semibold text-white">{m.apply}</h3>
      <p className="text-sm text-gray-400">{m.applyHint}</p>
      <div>
        <label htmlFor="org-name" className="field-label">
          {m.name}
        </label>
        <input
          id="org-name"
          required
          minLength={2}
          className="field"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        <div>
          <label htmlFor="org-type" className="field-label">
            {m.type}
          </label>
          <select
            id="org-type"
            className="field"
            value={orgType}
            onChange={(e) => setOrgType(e.target.value as OrgType)}
          >
            {ORG_TYPES.map((o) => (
              <option key={o} value={o}>
                {t.connect.orgTypes[o]}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="org-email" className="field-label">
            {m.email}
          </label>
          <input
            id="org-email"
            type="email"
            required
            className="field"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </div>
      </div>
      <div>
        <label htmlFor="org-web" className="field-label">
          {m.website}
        </label>
        <input
          id="org-web"
          type="url"
          placeholder="https://"
          className="field"
          value={website}
          onChange={(e) => setWebsite(e.target.value)}
        />
      </div>
      {error && (
        <p role="alert" className="text-sm text-ember-300">
          {error}
        </p>
      )}
      <div className="flex items-center gap-3">
        <button type="submit" className="btn-primary">
          {m.submitApply}
        </button>
        {done && (
          <span role="status" className="text-sm text-primary-300">
            {m.applied}
          </span>
        )}
      </div>
    </form>
  );
}

function AddMember({ orgId }: { orgId: string }) {
  const { t } = useTranslation();
  const m = t.connect.mine;
  const [email, setEmail] = useState("");
  const [state, setState] = useState<"idle" | "added" | string>("idle");
  return (
    <form
      className="mt-3 flex flex-wrap items-end gap-2"
      onSubmit={async (e) => {
        e.preventDefault();
        try {
          await communityAPI.addMember(orgId, email);
          setEmail("");
          setState("added");
        } catch (err) {
          setState(err instanceof Error ? err.message : String(err));
        }
      }}
    >
      <div className="min-w-0 flex-1">
        <label htmlFor={`add-${orgId}`} className="field-label text-xs">
          {m.addMember}
        </label>
        <input
          id={`add-${orgId}`}
          type="email"
          required
          className="field py-1.5"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
      </div>
      <button type="submit" className="btn-ghost py-1.5 text-xs">
        {m.add}
      </button>
      <p className="w-full text-xs text-gray-400" role="status">
        {state === "idle"
          ? m.addMemberHint
          : state === "added"
            ? m.added
            : state}
      </p>
    </form>
  );
}

export default function MyConnectionsPage() {
  const { t } = useTranslation();
  const m = t.connect.mine;
  const { me, status, refresh } = useAuthStore();
  const [connects, setConnects] = useState<Connect[] | null>(null);
  const [offers, setOffers] = useState<Offer[]>([]);

  useEffect(() => {
    if (status === "unknown") void refresh();
  }, [status, refresh]);

  const load = useCallback(async () => {
    const [c, o] = await Promise.all([
      communityAPI.connects(),
      communityAPI.offers({ mine: true }),
    ]);
    setConnects(c.data);
    setOffers(o.data);
  }, []);

  useEffect(() => {
    if (status === "signed-in") void load().catch(() => setConnects([]));
  }, [status, load]);

  if (status === "signed-out") {
    return (
      <div className="flex min-h-screen flex-col bg-gray-950">
        <Header />
        <main className="flex flex-1 flex-col items-center justify-center gap-4 px-4">
          <p className="text-gray-300">{t.connect.signInFirst}</p>
          <Link
            href={`/login?next=${encodeURIComponent("/connect/mine")}`}
            className="btn-primary"
          >
            {t.auth.signIn}
          </Link>
        </main>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col bg-gray-950">
      <Header />
      <main className="flex-1 px-4 py-8 md:px-8">
        <div className="mx-auto grid max-w-5xl gap-8 lg:grid-cols-[1fr_22rem]">
          <section aria-labelledby="connections-title">
            <h1
              id="connections-title"
              className="text-3xl font-semibold tracking-tight text-white"
            >
              {m.title}
            </h1>
            <h2 className="mt-6 text-sm font-semibold text-gray-300">
              {m.connections}
            </h2>
            {connects === null ? (
              <div className="mt-3 h-32 animate-pulse rounded-xl bg-gray-900" />
            ) : connects.length === 0 ? (
              <EmptyState
                className="mt-3"
                icon={Handshake}
                title={m.noConnections}
                action={
                  <Link href="/connect" className="btn-ghost">
                    {t.connect.title}
                  </Link>
                }
              />
            ) : (
              <ul className="mt-3 space-y-3">
                {connects.map((c) => (
                  <ConnectRow key={c.id} c={c} onChange={() => void load()} />
                ))}
              </ul>
            )}

            {offers.length > 0 && (
              <h2 className="mt-10 text-sm font-semibold text-gray-300">
                {m.myOffers}
              </h2>
            )}
            <ul className="mt-3 space-y-2">
              {offers.map((o) => (
                <li
                  key={o.id}
                  className="flex items-center justify-between gap-3 rounded-lg border border-gray-700/80 bg-gray-900 px-4 py-3"
                >
                  <span className="min-w-0 truncate text-sm text-gray-100">
                    {o.title}
                  </span>
                  {o.status === "open" ? (
                    <button
                      type="button"
                      className="text-xs font-medium text-gray-400 hover:text-ember-300"
                      onClick={async () => {
                        await communityAPI.updateOffer(o.id, {
                          status: "withdrawn",
                        });
                        void load();
                      }}
                    >
                      {m.withdraw}
                    </button>
                  ) : (
                    <span className="text-xs text-gray-500">{o.status}</span>
                  )}
                </li>
              ))}
            </ul>
          </section>

          <aside className="space-y-4" aria-labelledby="orgs-title">
            <ContributionsCard />
            <h2 id="orgs-title" className="text-sm font-semibold text-gray-300">
              {m.orgs}
            </h2>
            {me && me.memberships.length === 0 && (
              <EmptyState compact icon={Building2} title={m.noOrgs} />
            )}
            {me?.memberships.map(({ org, role }) => (
              <div
                key={org.id}
                className="rounded-xl border border-gray-700/80 bg-gray-900 p-4"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <Building2
                      className="h-4 w-4 text-gray-400"
                      aria-hidden="true"
                    />
                    <span className="font-medium text-white">{org.name}</span>
                    {org.verified && <VerifiedBadge compact />}
                  </div>
                  <StatusPill status={org.status} />
                </div>
                <p className="mt-1 text-xs text-gray-400">
                  {t.connect.orgTypes[org.orgType]}
                </p>
                {org.status === "approved" && role === "org_admin" && (
                  <AddMember orgId={org.id} />
                )}
              </div>
            ))}
            <ApplyOrg onDone={() => void refresh()} />
            {me?.isPlatformAdmin && (
              <Link href="/connect/admin" className="btn-ghost w-full">
                {t.connect.admin.title}
              </Link>
            )}
          </aside>
        </div>
      </main>
    </div>
  );
}
