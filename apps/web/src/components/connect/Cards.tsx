"use client";

import { EmptyState } from "@/components/ui/States";
import { useState } from "react";
import Link from "next/link";
import {
  LayoutGrid,
  Building2,
  ChevronDown,
  Handshake,
  Mail,
  MapPin,
  Users,
  SearchX,
} from "lucide-react";
import {
  communityAPI,
  type Match,
  type Need,
  type Offer,
} from "@/lib/api/community";
import { useTranslation } from "@/lib/i18n/useTranslation";
import { CategoryIcon } from "./CategoryIcon";
import { VerifiedBadge } from "./VerifiedBadge";

const PRIORITY_EDGE: Record<string, string> = {
  critical: "bg-ember-500",
  high: "bg-amber-400",
  medium: "bg-primary-400",
  low: "bg-gray-500",
};

function Categories({ items }: { items: string[] }) {
  const { t } = useTranslation();
  return (
    <ul className="flex flex-wrap gap-1.5">
      {items.map((c) => (
        <li
          key={c}
          className="flex items-center gap-1 rounded-full bg-gray-800 px-2 py-0.5 text-xs text-gray-200"
        >
          <CategoryIcon category={c} className="h-3 w-3" />
          {t.connect.categories[c as keyof typeof t.connect.categories] ?? c}
        </li>
      ))}
    </ul>
  );
}

function ScoreBar({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  return (
    <div
      className="h-1 w-full overflow-hidden rounded-full bg-gray-800"
      aria-hidden="true"
    >
      <div
        className="h-full rounded-full bg-primary-400 transition-[width] duration-500"
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}

function MatchRow({
  match,
  canPropose,
  onPropose,
  proposed,
}: {
  match: Match;
  canPropose: boolean;
  onPropose: () => void;
  proposed: boolean;
}) {
  const { t, lang } = useTranslation();
  const o = match.offer;
  return (
    <li className="rounded-lg border border-gray-800 bg-gray-950/60 p-3">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="font-medium text-gray-100">{o.title}</p>
          <p className="mt-0.5 text-xs text-gray-400">
            {t.connect.offerTypes[o.offerType]}
            {o.quantity
              ? ` · ${o.quantity.toLocaleString(lang)} ${o.unit ?? ""}`
              : ""}
            {match.distanceKm != null
              ? ` · ${t.connect.away.replace("{km}", String(Math.round(match.distanceKm)))}`
              : ""}
          </p>
        </div>
        <span className="shrink-0 text-sm font-semibold text-primary-300">
          {t.connect.match.replace(
            "{pct}",
            String(Math.round(match.score * 100)),
          )}
        </span>
      </div>
      <div className="mt-2">
        <ScoreBar score={match.score} />
      </div>
      <ul className="mt-2 flex flex-wrap gap-1.5">
        {match.reasons.map((r) => (
          <li
            key={r}
            className="rounded bg-primary-400/10 px-1.5 py-0.5 text-xs text-primary-200"
          >
            {t.connect.reasons[r as keyof typeof t.connect.reasons] ?? r}
          </li>
        ))}
      </ul>
      {canPropose && (
        <button
          type="button"
          onClick={onPropose}
          disabled={proposed}
          className="btn-ghost mt-3 w-full py-1.5 text-xs"
        >
          <Handshake className="h-3.5 w-3.5" aria-hidden="true" />
          {proposed ? t.connect.proposed : t.connect.propose}
        </button>
      )}
    </li>
  );
}

export function NeedCard({
  need,
  signedIn,
  myOpenOffers,
}: {
  need: Need;
  signedIn: boolean;
  myOpenOffers: Offer[];
}) {
  const { t, lang } = useTranslation();
  const [open, setOpen] = useState(false);
  const [matches, setMatches] = useState<Match[] | null>(null);
  const [proposed, setProposed] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);
  const [offerChoice, setOfferChoice] = useState("");

  const toggle = async () => {
    const next = !open;
    setOpen(next);
    if (next && matches === null) {
      try {
        setMatches((await communityAPI.matches(need.id)).data);
      } catch {
        setError(t.connect.loadFailed);
        setMatches([]);
      }
    }
  };

  const propose = async (offerId: string) => {
    setError(null);
    try {
      await communityAPI.propose(need.id, offerId);
      setProposed((s) => new Set(s).add(offerId));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  // Offer authors (not members of this org) can put one of their offers forward
  const canOfferMine = signedIn && !need.canEdit && need.status === "open";

  return (
    <article className="relative overflow-hidden rounded-xl border border-gray-700/80 bg-gray-900 p-5">
      <span
        aria-hidden="true"
        className={`absolute inset-y-0 left-0 w-1 ${PRIORITY_EDGE[need.priority]}`}
      />
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <span className="font-semibold text-gray-100">
          {t.connect.priority[need.priority]}
        </span>
        {need.status !== "open" && (
          <span className="rounded bg-gray-800 px-1.5 py-0.5 text-gray-300">
            {need.status}
          </span>
        )}
        <Categories items={need.categories} />
      </div>
      <h3 className="mt-2 text-lg font-semibold leading-snug text-white">
        {need.title}
      </h3>
      {need.description && (
        <p className="mt-1 line-clamp-3 text-sm text-gray-300">
          {need.description}
        </p>
      )}
      <dl className="mt-3 grid gap-x-5 gap-y-1.5 text-sm text-gray-300 sm:grid-cols-2">
        <div className="flex items-center gap-2">
          <Building2 className="h-4 w-4 text-gray-500" aria-hidden="true" />
          <dt className="sr-only">{t.connect.form.org}</dt>
          <dd className="flex items-center gap-1.5">
            {need.org.name}
            {need.org.verified && <VerifiedBadge compact />}
          </dd>
        </div>
        {need.placeName && (
          <div className="flex items-center gap-2">
            <MapPin className="h-4 w-4 text-gray-500" aria-hidden="true" />
            <dt className="sr-only">{t.connect.form.place}</dt>
            <dd>{need.placeName}</dd>
          </div>
        )}
        {need.quantity != null && (
          <div className="flex items-center gap-2">
            <span className="w-4 text-center text-gray-500" aria-hidden="true">
              #
            </span>
            <dt className="sr-only">{t.connect.form.quantity}</dt>
            <dd>
              {need.quantity.toLocaleString(lang)} {need.unit}
            </dd>
          </div>
        )}
        {need.beneficiaries != null && need.beneficiaries > 0 && (
          <div className="flex items-center gap-2">
            <Users className="h-4 w-4 text-gray-500" aria-hidden="true" />
            <dt className="sr-only">{t.connect.form.beneficiaries}</dt>
            <dd>
              {t.connect.people.replace(
                "{n}",
                need.beneficiaries.toLocaleString(lang),
              )}
            </dd>
          </div>
        )}
        <div className="flex items-center gap-2">
          <Mail className="h-4 w-4 text-gray-500" aria-hidden="true" />
          <dt className="sr-only">{t.connect.contact}</dt>
          <dd>
            <a
              href={`mailto:${need.contactEmail}`}
              className="text-primary-300 hover:underline"
            >
              {need.contactEmail}
            </a>
          </dd>
        </div>
      </dl>

      {need.planId && (
        <Link
          href={`/plan?id=${need.planId}`}
          className="mt-3 inline-flex items-center gap-1.5 text-sm font-medium text-primary-300 hover:underline"
        >
          <LayoutGrid className="h-4 w-4" aria-hidden="true" />
          {t.plans.view}
        </Link>
      )}
      <div className="mt-4 flex flex-wrap gap-2">
        <button
          type="button"
          onClick={toggle}
          aria-expanded={open}
          className="btn-ghost py-1.5 text-xs"
        >
          <ChevronDown
            className={`h-3.5 w-3.5 transition-transform ${open ? "rotate-180" : ""}`}
            aria-hidden="true"
          />
          {open ? t.connect.hideMatches : t.connect.seeMatches}
        </button>
        {canOfferMine &&
          (myOpenOffers.length > 0 ? (
            <div className="flex items-center gap-2">
              <label htmlFor={`offer-${need.id}`} className="sr-only">
                {t.connect.chooseOffer}
              </label>
              <select
                id={`offer-${need.id}`}
                value={offerChoice}
                onChange={(e) => setOfferChoice(e.target.value)}
                className="field py-1.5 text-xs"
              >
                <option value="">{t.connect.chooseOffer}</option>
                {myOpenOffers.map((o) => (
                  <option key={o.id} value={o.id}>
                    {o.title}
                  </option>
                ))}
              </select>
              <button
                type="button"
                disabled={!offerChoice || proposed.has(offerChoice)}
                onClick={() => propose(offerChoice)}
                className="btn-primary shrink-0 py-1.5 text-xs"
              >
                <Handshake className="h-3.5 w-3.5" aria-hidden="true" />
                {proposed.has(offerChoice)
                  ? t.connect.proposed
                  : t.connect.offerThis}
              </button>
            </div>
          ) : (
            <p className="self-center text-xs text-gray-400">
              {t.connect.noOwnOffers}
            </p>
          ))}
      </div>
      {error && (
        <p role="alert" className="mt-3 text-sm text-ember-300">
          {error}
        </p>
      )}
      {open && (
        <div className="mt-4" aria-live="polite">
          {matches === null ? (
            <div className="h-16 animate-pulse rounded-lg bg-gray-800" />
          ) : matches.length === 0 ? (
            <EmptyState compact icon={SearchX} title={t.connect.noMatches} />
          ) : (
            <ul className="grid gap-2 md:grid-cols-2">
              {matches.map((m) => (
                <MatchRow
                  key={m.offer.id}
                  match={m}
                  canPropose={need.canEdit && !m.offer.isMine}
                  proposed={proposed.has(m.offer.id)}
                  onPropose={() => propose(m.offer.id)}
                />
              ))}
            </ul>
          )}
        </div>
      )}
    </article>
  );
}

export function OfferCard({ offer }: { offer: Offer }) {
  const { t, lang } = useTranslation();
  return (
    <article className="rounded-xl border border-gray-700/80 bg-gray-900 p-5">
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <span className="rounded bg-primary-400/15 px-1.5 py-0.5 font-semibold text-primary-200">
          {t.connect.offerTypes[offer.offerType]}
        </span>
        <Categories items={offer.categories} />
      </div>
      <h3 className="mt-2 font-semibold text-white">{offer.title}</h3>
      {offer.description && (
        <p className="mt-1 line-clamp-3 text-sm text-gray-300">
          {offer.description}
        </p>
      )}
      <p className="mt-2 text-sm text-gray-400">
        {offer.quantity
          ? `${offer.quantity.toLocaleString(lang)} ${offer.unit ?? ""}`
          : ""}
        {offer.quantity && offer.placeName ? " · " : ""}
        {offer.placeName ?? ""}
      </p>
    </article>
  );
}
