"use client";

import { useCallback, useEffect, useState } from "react";
import { Check, X } from "lucide-react";
import { Header } from "@/components/layout/Header";
import { VerifiedBadge } from "@/components/connect/VerifiedBadge";
import { communityAPI, type OrgAdminView } from "@/lib/api/community";
import { useTranslation } from "@/lib/i18n/useTranslation";
import { useAuthStore } from "@/store/authStore";

function Review({ org, onDone }: { org: OrgAdminView; onDone: () => void }) {
  const { t } = useTranslation();
  const a = t.connect.admin;
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const run = async (fn: () => Promise<unknown>) => {
    setBusy(true);
    try {
      await fn();
      onDone();
    } finally {
      setBusy(false);
    }
  };
  return (
    <li className="rounded-xl border border-gray-800 bg-gray-900 p-5">
      <p className="text-lg font-semibold text-white">{org.name}</p>
      <p className="mt-1 text-sm text-gray-300">
        {t.connect.orgTypes[org.orgType]} · {org.primaryEmail}
        {org.website && (
          <>
            {" · "}
            <a
              href={org.website}
              target="_blank"
              rel="noopener noreferrer"
              className="text-primary-300 hover:underline"
            >
              {org.website}
            </a>
          </>
        )}
      </p>
      <p className="mt-1 text-xs text-gray-400">
        {a.requestedBy.replace("{email}", org.requestedByEmail)}
      </p>
      <label htmlFor={`reason-${org.id}`} className="field-label mt-4 text-xs">
        {a.reason}
      </label>
      <input
        id={`reason-${org.id}`}
        className="field"
        maxLength={500}
        value={reason}
        onChange={(e) => setReason(e.target.value)}
      />
      <div className="mt-3 flex gap-2">
        <button
          type="button"
          className="btn-primary"
          disabled={busy}
          onClick={() => run(() => communityAPI.approveOrg(org.id))}
        >
          <Check className="h-4 w-4" aria-hidden="true" />
          {a.approve}
        </button>
        <button
          type="button"
          className="btn-ghost"
          disabled={busy}
          onClick={() =>
            run(() => communityAPI.rejectOrg(org.id, reason || undefined))
          }
        >
          <X className="h-4 w-4" aria-hidden="true" />
          {a.reject}
        </button>
      </div>
    </li>
  );
}

export default function AdminPage() {
  const { t } = useTranslation();
  const a = t.connect.admin;
  const { me, status, refresh } = useAuthStore();
  const [orgs, setOrgs] = useState<OrgAdminView[] | null>(null);
  const [approved, setApproved] = useState<OrgAdminView[]>([]);

  useEffect(() => {
    if (status === "unknown") void refresh();
  }, [status, refresh]);

  const load = useCallback(() => {
    communityAPI
      .orgsForReview("pending")
      .then(setOrgs)
      .catch(() => setOrgs([]));
    communityAPI
      .orgsForReview("approved")
      .then(setApproved)
      .catch(() => setApproved([]));
  }, []);

  useEffect(() => {
    if (me?.isPlatformAdmin) load();
  }, [me, load]);

  return (
    <div className="flex min-h-screen flex-col bg-gray-950">
      <Header />
      <main className="flex-1 px-4 py-8 md:px-8">
        <div className="mx-auto max-w-3xl">
          <h1 className="text-3xl font-semibold tracking-tight text-white">
            {a.title}
          </h1>
          {status !== "unknown" && !me?.isPlatformAdmin ? (
            <p className="mt-4 text-gray-300">{a.notAdmin}</p>
          ) : orgs === null ? (
            <div className="mt-6 h-40 animate-pulse rounded-xl bg-gray-900" />
          ) : orgs.length === 0 ? (
            <p className="mt-6 rounded-xl border border-dashed border-gray-700 px-5 py-8 text-gray-400">
              {a.none}
            </p>
          ) : (
            <ul className="mt-6 space-y-3">
              {orgs.map((o) => (
                <Review key={o.id} org={o} onDone={load} />
              ))}
            </ul>
          )}

          {me?.isPlatformAdmin && approved.length > 0 && (
            <section className="mt-10" aria-labelledby="approved-title">
              <h2
                id="approved-title"
                className="text-sm font-semibold text-gray-300"
              >
                {t.badges.approvedOrgs}
              </h2>
              <ul className="mt-3 divide-y divide-gray-800 rounded-xl border border-gray-800 bg-gray-900">
                {approved.map((o) => (
                  <li
                    key={o.id}
                    className="flex flex-wrap items-center gap-3 px-4 py-3"
                  >
                    <span className="min-w-0 flex-1">
                      <span className="flex items-center gap-1.5 font-medium text-gray-100">
                        {o.name}
                        {o.verified && <VerifiedBadge compact />}
                      </span>
                      <span className="text-xs text-gray-400">
                        {t.connect.orgTypes[o.orgType]}
                      </span>
                    </span>
                    <button
                      type="button"
                      className={
                        o.verified
                          ? "btn-ghost py-1.5 text-xs"
                          : "btn-primary py-1.5 text-xs"
                      }
                      onClick={async () => {
                        await communityAPI.verifyOrg(o.id, !o.verified);
                        load();
                      }}
                    >
                      {o.verified ? t.badges.unverify : t.badges.verify}
                    </button>
                  </li>
                ))}
              </ul>
            </section>
          )}
        </div>
      </main>
    </div>
  );
}
