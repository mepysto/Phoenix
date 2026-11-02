/**
 * Accounts, organisations, needs, offers and connections (Phase 2).
 *
 * Uses the session cookie set by /auth/verify, so every request includes
 * credentials. Responses are camel-cased like the rest of the client.
 */

import { API_URL, APIError, transformKeys } from "./client";
import type { components } from "./schema.d.ts";

type S = components["schemas"];
type Camel<T> = CamelDeep<T>;
type SnakeToCamel<K extends string> = K extends `${infer A}_${infer B}`
  ? `${A}${Capitalize<SnakeToCamel<B>>}`
  : K;
type CamelDeep<T> =
  T extends Array<infer U>
    ? Array<CamelDeep<U>>
    : T extends object
      ? {
          [K in keyof T as K extends string ? SnakeToCamel<K> : K]: CamelDeep<
            T[K]
          >;
        }
      : T;

export type Me = Camel<S["Me"]>;
export type OrgSummary = Camel<S["OrgSummary"]>;
export type OrgAdminView = Camel<S["OrgAdminView"]>;
export type Need = Camel<S["NeedOut"]>;
export type Offer = Camel<S["OfferOut"]>;
export type Match = Camel<S["MatchOut"]>;
export type Connect = Camel<S["ConnectOut"]>;
export type Disclosure = Camel<S["DisclosureOut"]>;
export type Contributions = Camel<S["Contributions"]>;
export type Category = S["NeedCreate"]["categories"][number];
export type OrgType = S["OrgType"];
export type NeedPriority = S["NeedPriority"];
export type OfferType = S["OfferType"];
export type NeedCreate = S["NeedCreate"];
export type OfferCreate = S["OfferCreate"];

export const CATEGORIES: Category[] = [
  "shelter",
  "water",
  "sanitation",
  "food",
  "health",
  "power",
  "communications",
  "logistics",
  "education",
  "protection",
  "cash",
  "other",
];

async function call<T>(
  path: string,
  init: RequestInit & { json?: unknown } = {},
): Promise<T> {
  const { json, ...rest } = init;
  const response = await fetch(`${API_URL}${path}`, {
    ...rest,
    credentials: "include",
    headers:
      json !== undefined
        ? { "content-type": "application/json", ...rest.headers }
        : rest.headers,
    body: json !== undefined ? JSON.stringify(json) : rest.body,
  });
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = (await response.json()) as { detail?: unknown };
      if (typeof body.detail === "string") detail = body.detail;
      else if (Array.isArray(body.detail))
        detail = String((body.detail[0] as { msg?: string })?.msg ?? detail);
    } catch {
      // keep statusText
    }
    throw new APIError(response.status, detail);
  }
  if (response.status === 204) return undefined as T;
  return transformKeys<T>(await response.json());
}

const qs = (
  params: Record<string, string | number | boolean | undefined | null>,
) => {
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(params))
    if (v !== undefined && v !== null && v !== "") p.set(k, String(v));
  const s = p.toString();
  return s ? `?${s}` : "";
};

export const authAPI = {
  requestLink: (email: string, redirectPath?: string) =>
    call<{ sent: boolean; devLink: string | null }>("/api/v1/auth/login-link", {
      method: "POST",
      json: { email, redirect_path: redirectPath },
    }),
  verify: (token: string) =>
    call<{ user: Me; redirectPath: string }>("/api/v1/auth/verify", {
      method: "POST",
      json: { token },
    }),
  me: () => call<Me>("/api/v1/auth/me"),
  logout: () => call<void>("/api/v1/auth/logout", { method: "POST" }),
  contributions: () => call<Contributions>("/api/v1/auth/me/contributions"),
};

const C = "/api/v1/community";

export const communityAPI = {
  applyOrg: (body: {
    name: string;
    org_type: OrgType;
    primary_email: string;
    website?: string | null;
  }) => call<OrgSummary>(`${C}/orgs`, { method: "POST", json: body }),
  addMember: (orgId: string, email: string) =>
    call<unknown>(`${C}/orgs/${orgId}/members`, {
      method: "POST",
      json: { email },
    }),
  orgsForReview: (status?: string) =>
    call<OrgAdminView[]>(`${C}/admin/orgs${qs({ status })}`),
  approveOrg: (id: string) =>
    call<OrgSummary>(`${C}/admin/orgs/${id}/approve`, { method: "POST" }),
  verifyOrg: (id: string, verified: boolean) =>
    call<OrgSummary>(`${C}/admin/orgs/${id}/${verified ? "verify" : "unverify"}`, { method: "POST" }),
  rejectOrg: (id: string, reason?: string) =>
    call<OrgSummary>(`${C}/admin/orgs/${id}/reject`, {
      method: "POST",
      json: { reason },
    }),

  needs: (
    f: {
      eventId?: string;
      category?: Category;
      status?: string;
      limit?: number;
    } = {},
  ) =>
    call<{ data: Need[]; total: number }>(
      `${C}/needs${qs({ event_id: f.eventId, category: f.category, status: f.status, limit: f.limit })}`,
    ),
  createNeed: (body: NeedCreate) =>
    call<Need>(`${C}/needs`, { method: "POST", json: body }),
  updateNeed: (
    id: string,
    body: Partial<{ status: string; priority: NeedPriority }>,
  ) => call<Need>(`${C}/needs/${id}`, { method: "PATCH", json: body }),
  matches: (needId: string) =>
    call<{ needId: string; data: Match[] }>(`${C}/needs/${needId}/matches`),

  offers: (
    f: {
      eventId?: string;
      category?: Category;
      mine?: boolean;
      status?: string;
    } = {},
  ) =>
    call<{ data: Offer[]; total: number }>(
      `${C}/offers${qs({ event_id: f.eventId, category: f.category, mine: f.mine, status: f.status })}`,
    ),
  createOffer: (body: OfferCreate) =>
    call<Offer>(`${C}/offers`, { method: "POST", json: body }),
  updateOffer: (id: string, body: Partial<{ status: string }>) =>
    call<Offer>(`${C}/offers/${id}`, { method: "PATCH", json: body }),

  connects: () => call<{ data: Connect[] }>(`${C}/connects`),
  propose: (needId: string, offerId: string, message?: string) =>
    call<Connect>(`${C}/connects`, {
      method: "POST",
      json: { need_id: needId, offer_id: offerId, message },
    }),
  approve: (id: string) =>
    call<Connect>(`${C}/connects/${id}/approve`, { method: "POST" }),
  decline: (id: string) =>
    call<Connect>(`${C}/connects/${id}/decline`, { method: "POST" }),

  disclosures: (eventId: string) =>
    call<{ data: Disclosure[] }>(`${C}/events/${eventId}/disclosures`),
  publishDisclosure: (
    eventId: string,
    body: { org_id: string; title: string; body: string },
  ) =>
    call<Disclosure>(`${C}/events/${eventId}/disclosures`, {
      method: "POST",
      json: body,
    }),
};

// --- site plans ---------------------------------------------------------------

export type PlanOut = Camel<S["PlanOut"]>;
export type PlanSummary = Camel<S["PlanSummary"]>;
export type PlanItemsWire = S["PlanContent"]["items"];

export const plansAPI = {
  list: (f: { eventId?: string; mine?: boolean } = {}) =>
    call<{ data: PlanSummary[] }>(`/api/v1/plans${qs({ event_id: f.eventId, mine: f.mine })}`),
  get: (id: string, version?: number) => call<PlanOut>(`/api/v1/plans/${id}${qs({ version })}`),
  create: (body: S["PlanCreate"]) => call<PlanOut>("/api/v1/plans", { method: "POST", json: body }),
  saveVersion: (id: string, body: S["PlanContent"]) =>
    call<PlanOut>(`/api/v1/plans/${id}/versions`, { method: "POST", json: body }),
  update: (id: string, body: S["PlanUpdate"]) => call<PlanOut>(`/api/v1/plans/${id}`, { method: "PATCH", json: body }),
  fork: (id: string, version?: number) =>
    call<PlanOut>(`/api/v1/plans/${id}/fork`, { method: "POST", json: { version } }),
  attachToNeed: (needId: string, planId: string | null) =>
    call<Need>(`/api/v1/community/needs/${needId}`, { method: "PATCH", json: { plan_id: planId } }),
};

// --- design challenges ------------------------------------------------------

export type ChallengeSummary = Camel<S["ChallengeSummary"]>;
export type ChallengeOut = Camel<S["ChallengeOut"]>;
export type ChallengeEntry = Camel<S["EntryOut"]>;

export const challengesAPI = {
  list: (eventId?: string) => call<{ data: ChallengeSummary[] }>(`/api/v1/challenges${qs({ event_id: eventId })}`),
  get: (id: string) => call<ChallengeOut>(`/api/v1/challenges/${id}`),
  create: (body: S["ChallengeCreate"]) => call<ChallengeOut>("/api/v1/challenges", { method: "POST", json: body }),
  enter: (id: string, planId: string) =>
    call<ChallengeOut>(`/api/v1/challenges/${id}/entries`, { method: "POST", json: { plan_id: planId } }),
  vote: (entryId: string, on: boolean) =>
    call<ChallengeOut>(`/api/v1/challenges/entries/${entryId}/${on ? "vote" : "unvote"}`, { method: "POST" }),
  select: (id: string, entryId: string | null) =>
    call<ChallengeOut>(`/api/v1/challenges/${id}/select`, { method: "POST", json: { entry_id: entryId } }),
};
