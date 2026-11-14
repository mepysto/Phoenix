"use client";

import { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { HandHeart, Inbox, Plus } from "lucide-react";
import { EmptyState } from "@/components/ui/States";
import { Header } from "@/components/layout/Header";
import { NeedCard, OfferCard } from "@/components/connect/Cards";
import { CategoryIcon } from "@/components/connect/CategoryIcon";
import {
  NeedForm,
  OfferForm,
  type EventChoice,
} from "@/components/connect/Forms";
import { SlideOver } from "@/components/connect/SlideOver";
import { eventsAPI } from "@/lib/api/client";
import {
  CATEGORIES,
  communityAPI,
  type Category,
  type Need,
  type Offer,
} from "@/lib/api/community";
import { getEventPosition } from "@/lib/eventPosition";
import { useTranslation } from "@/lib/i18n/useTranslation";
import { approvedOrgs, useAuthStore } from "@/store/authStore";

type Tab = "needs" | "offers";

function ConnectBoard() {
  const { t } = useTranslation();
  const params = useSearchParams();
  const eventFilter = params.get("event") ?? undefined;
  const { me, status, refresh } = useAuthStore();
  const [tab, setTab] = useState<Tab>("needs");
  const [category, setCategory] = useState<Category | undefined>();
  const [needs, setNeeds] = useState<Need[] | null>(null);
  const [offers, setOffers] = useState<Offer[] | null>(null);
  const [myOffers, setMyOffers] = useState<Offer[]>([]);
  const [events, setEvents] = useState<EventChoice[]>([]);
  const [error, setError] = useState(false);
  const [panel, setPanel] = useState<"need" | "offer" | null>(null);
  const orgs = useMemo(() => approvedOrgs(me), [me]);

  useEffect(() => {
    if (status === "unknown") void refresh();
  }, [status, refresh]);

  const load = useCallback(async () => {
    setError(false);
    try {
      const [n, o] = await Promise.all([
        communityAPI.needs({
          eventId: eventFilter,
          category,
          status: "open",
          limit: 100,
        }),
        communityAPI.offers({ eventId: eventFilter, category, status: "open" }),
      ]);
      setNeeds(n.data);
      setOffers(o.data);
    } catch {
      setError(true);
      setNeeds([]);
      setOffers([]);
    }
  }, [eventFilter, category]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (status !== "signed-in") return;
    communityAPI
      .offers({ mine: true, status: "open" })
      .then((r) => setMyOffers(r.data))
      .catch(() => setMyOffers([]));
  }, [status, panel]);

  useEffect(() => {
    eventsAPI
      .list({ isActive: true }, 200)
      .then((r) =>
        setEvents(
          r.data.map((e) => {
            const p = getEventPosition(e);
            return { id: e.id, title: e.title, lat: p?.lat, lng: p?.lng };
          }),
        ),
      )
      .catch(() => setEvents([]));
  }, []);

  const eventTitle = events.find((e) => e.id === eventFilter)?.title;
  const list = tab === "needs" ? needs : offers;

  return (
    <main className="flex-1 px-4 py-8 md:px-8">
      <div className="mx-auto max-w-5xl">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div className="max-w-2xl">
            <h1 className="text-3xl font-semibold tracking-tight text-white">
              {t.connect.title}
            </h1>
            {eventTitle && (
              <p className="mt-1 text-sm font-medium text-ember-300">
                {eventTitle}
              </p>
            )}
            <p className="mt-2 text-gray-300">{t.connect.intro}</p>
          </div>
          <div className="flex gap-2">
            {status === "signed-in" ? (
              <>
                {orgs.length > 0 && (
                  <button
                    type="button"
                    className="btn-ghost"
                    onClick={() => setPanel("need")}
                  >
                    <Plus className="h-4 w-4" aria-hidden="true" />
                    {t.connect.postNeed}
                  </button>
                )}
                <button
                  type="button"
                  className="btn-primary"
                  onClick={() => setPanel("offer")}
                >
                  <HandHeart className="h-4 w-4" aria-hidden="true" />
                  {t.connect.offerHelp}
                </button>
                <Link href="/connect/mine" className="btn-ghost">
                  <Inbox className="h-4 w-4" aria-hidden="true" />
                  {t.connect.mine.title}
                </Link>
              </>
            ) : (
              <Link
                href={`/login?next=${encodeURIComponent("/connect")}`}
                className="btn-primary"
              >
                <HandHeart className="h-4 w-4" aria-hidden="true" />
                {t.connect.signInToOffer}
              </Link>
            )}
          </div>
        </div>

        <div className="mt-8 flex flex-wrap items-center justify-between gap-4 border-b border-gray-800">
          <div
            role="tablist"
            aria-label={t.connect.title}
            className="flex gap-6"
          >
            {(["needs", "offers"] as const).map((k) => (
              <button
                key={k}
                role="tab"
                aria-selected={tab === k}
                onClick={() => setTab(k)}
                className={`-mb-px border-b-2 pb-3 text-sm font-medium ${
                  tab === k
                    ? "border-primary-400 text-white"
                    : "border-transparent text-gray-400 hover:text-gray-200"
                }`}
              >
                {k === "needs" ? t.connect.tabNeeds : t.connect.tabOffers}
                <span className="ml-2 rounded-full bg-gray-800 px-2 py-0.5 text-xs text-gray-300">
                  {(k === "needs" ? needs : offers)?.length ?? "–"}
                </span>
              </button>
            ))}
          </div>
        </div>

        <div
          className="mt-4 flex gap-2 overflow-x-auto pb-2"
          role="group"
          aria-label={t.connect.form.categories}
        >
          <button
            type="button"
            aria-pressed={!category}
            onClick={() => setCategory(undefined)}
            className={`shrink-0 rounded-full border px-3 py-1.5 text-xs font-medium ${
              !category
                ? "border-primary-400 bg-primary-400/15 text-primary-100"
                : "border-gray-700 text-gray-300"
            }`}
          >
            {t.connect.allCategories}
          </button>
          {CATEGORIES.map((c) => (
            <button
              key={c}
              type="button"
              aria-pressed={category === c}
              onClick={() => setCategory(category === c ? undefined : c)}
              className={`flex shrink-0 items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-medium ${
                category === c
                  ? "border-primary-400 bg-primary-400/15 text-primary-100"
                  : "border-gray-700 text-gray-300"
              }`}
            >
              <CategoryIcon category={c} className="h-3.5 w-3.5" />
              {t.connect.categories[c]}
            </button>
          ))}
        </div>

        <section
          role="tabpanel"
          className="mt-5 space-y-3"
          aria-busy={list === null}
        >
          {error && (
            <p
              role="alert"
              className="rounded-lg border border-ember-600/50 px-4 py-3 text-sm text-ember-300"
            >
              {t.connect.loadFailed}
            </p>
          )}
          {list === null ? (
            [0, 1, 2].map((i) => (
              <div
                key={i}
                className="h-40 animate-pulse rounded-xl bg-gray-900"
              />
            ))
          ) : list.length === 0 ? (
            <EmptyState
              icon={tab === "needs" ? HandHeart : Inbox}
              title={tab === "needs" ? t.connect.noNeeds : t.connect.noOffers}
              body={
                // How needs and offers meet, instead of pointing at a menu (UX plan A-01)
                <ol className="mx-auto mt-2 max-w-md space-y-2 text-start">
                  {[t.ux.helpStep1, t.ux.helpStep2, t.ux.helpStep3].map((step, i) => (
                    <li key={step} className="flex gap-3 text-sm text-gray-300">
                      <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary-400/15 text-xs font-semibold text-primary-200">
                        {i + 1}
                      </span>
                      {step}
                    </li>
                  ))}
                </ol>
              }
              action={
                category ? (
                  <button
                    type="button"
                    className="btn-ghost"
                    onClick={() => setCategory(undefined)}
                  >
                    {t.ux.showAll}
                  </button>
                ) : orgs.length === 0 ? (
                  <Link href={status === "signed-in" ? "/connect/mine" : "/login"} className="btn-ghost">
                    {t.ux.orgApply}
                  </Link>
                ) : undefined
              }
            />
          ) : tab === "needs" ? (
            needs!.map((n) => (
              <NeedCard
                key={n.id}
                need={n}
                signedIn={status === "signed-in"}
                myOpenOffers={myOffers}
              />
            ))
          ) : (
            <div className="grid gap-3 md:grid-cols-2">
              {offers!.map((o) => (
                <OfferCard key={o.id} offer={o} />
              ))}
            </div>
          )}
        </section>
      </div>

      <SlideOver
        open={panel === "need"}
        title={t.connect.postNeed}
        onClose={() => setPanel(null)}
        closeLabel={t.common.close}
      >
        <NeedForm
          orgs={orgs}
          events={events}
          initialEventId={eventFilter}
          onCancel={() => setPanel(null)}
          onDone={() => {
            setPanel(null);
            setTab("needs");
            void load();
          }}
        />
      </SlideOver>
      <SlideOver
        open={panel === "offer"}
        title={t.connect.offerHelp}
        onClose={() => setPanel(null)}
        closeLabel={t.common.close}
      >
        <OfferForm
          events={events}
          initialEventId={eventFilter}
          onCancel={() => setPanel(null)}
          onDone={() => {
            setPanel(null);
            setTab("offers");
            void load();
          }}
        />
      </SlideOver>
    </main>
  );
}

export default function ConnectPage() {
  return (
    <div className="flex min-h-screen flex-col bg-gray-950">
      <Header />
      <Suspense>
        <ConnectBoard />
      </Suspense>
    </div>
  );
}
