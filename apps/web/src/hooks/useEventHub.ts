"use client";

import { useEffect, useState } from "react";
import {
  APIError,
  eventsAPI,
  fetchEventDamage,
  type ApiDamageSummary,
  type ApiDisasterEventDetail,
} from "@/lib/api/client";
import {
  challengesAPI,
  communityAPI,
  plansAPI,
  type ChallengeSummary,
  type Disclosure,
  type Need,
  type PlanSummary,
} from "@/lib/api/community";

/** Everything the event page shows, loaded once so the tabs can show counts */
export interface EventHub {
  event: ApiDisasterEventDetail | null;
  loading: boolean;
  /** HTTP status of a failed load (404 = no such event; 0 = network) */
  errorStatus: number | null;
  damage: ApiDamageSummary | null;
  damageFailed: boolean;
  needs: Need[] | null;
  needsTotal: number;
  plans: PlanSummary[] | null;
  challenges: ChallengeSummary[] | null;
  updates: Disclosure[] | null;
  addUpdate: (update: Disclosure) => void;
}

export function useEventHub(eventId: string): EventHub {
  const [event, setEvent] = useState<ApiDisasterEventDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [errorStatus, setErrorStatus] = useState<number | null>(null);
  const [damage, setDamage] = useState<ApiDamageSummary | null>(null);
  const [damageFailed, setDamageFailed] = useState(false);
  const [needs, setNeeds] = useState<Need[] | null>(null);
  const [needsTotal, setNeedsTotal] = useState(0);
  const [plans, setPlans] = useState<PlanSummary[] | null>(null);
  const [challenges, setChallenges] = useState<ChallengeSummary[] | null>(null);
  const [updates, setUpdates] = useState<Disclosure[] | null>(null);

  useEffect(() => {
    if (!eventId) return;
    const controller = new AbortController();
    setLoading(true);
    setErrorStatus(null);
    setDamage(null);
    setDamageFailed(false);

    eventsAPI
      .get(eventId)
      .then((data) => !controller.signal.aborted && setEvent(data))
      .catch((err) => {
        if (!controller.signal.aborted) setErrorStatus(err instanceof APIError ? err.statusCode : 0);
      })
      .finally(() => !controller.signal.aborted && setLoading(false));
    fetchEventDamage(eventId, controller.signal)
      .then(setDamage)
      .catch(() => !controller.signal.aborted && setDamageFailed(true));
    communityAPI
      .needs({ eventId, status: "open", limit: 20 })
      .then((r) => {
        setNeeds(r.data);
        setNeedsTotal(r.total ?? r.data.length);
      })
      .catch(() => setNeeds([]));
    plansAPI
      .list({ eventId })
      .then((r) => setPlans(r.data))
      .catch(() => setPlans([]));
    challengesAPI
      .list(eventId)
      .then((r) => setChallenges(r.data))
      .catch(() => setChallenges([]));
    communityAPI
      .disclosures(eventId)
      .then((r) => setUpdates(r.data))
      .catch(() => setUpdates([]));

    return () => controller.abort();
  }, [eventId]);

  return {
    event,
    loading,
    errorStatus,
    damage,
    damageFailed,
    needs,
    needsTotal,
    plans,
    challenges,
    updates,
    addUpdate: (update) => setUpdates((u) => [update, ...(u ?? [])]),
  };
}
