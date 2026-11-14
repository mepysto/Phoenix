import { EVENT_TYPES } from "@phoenix/shared/constants";
import type { EventFilter, EventSort, EventType, SeverityLevel } from "@/lib/api/client";
import { ALL_SEVERITY_LEVELS, parseList } from "@/lib/map/urlState";

/**
 * Event filters in the query string, shared by the map (/) and the disaster
 * list (/events) so moving between them keeps what the reader chose
 * (UX plan 4.2). The map already writes t (types) and s (severities).
 *
 *   ?t=flood,storm&s=high,critical&q=valencia&period=7&sort=recent
 */
export type Period = "1" | "7" | "30";

export interface EventQuery {
  types?: EventType[];
  severities?: SeverityLevel[];
  q?: string;
  /** Started within this many days; absent = any time */
  period?: Period;
  sort: EventSort;
}

export const PERIODS: Period[] = ["1", "7", "30"];
const SORTS: EventSort[] = ["importance", "recent", "affected"];
export const DEFAULT_SORT: EventSort = "importance";
/** Keys that travel between the map and the list */
const SHARED_KEYS = ["t", "s", "q", "period"] as const;

export function parseEventQuery(params: URLSearchParams): EventQuery {
  const query: EventQuery = { sort: DEFAULT_SORT };
  const types = parseList(params.get("t"), EVENT_TYPES as EventType[]);
  if (types) query.types = types;
  const severities = parseList(params.get("s"), ALL_SEVERITY_LEVELS);
  if (severities) query.severities = severities;
  const q = params.get("q")?.trim();
  if (q) query.q = q.slice(0, 100);
  const period = params.get("period");
  if ((PERIODS as string[]).includes(period ?? "")) query.period = period as Period;
  const sort = params.get("sort");
  if ((SORTS as string[]).includes(sort ?? "")) query.sort = sort as EventSort;
  return query;
}

export function serializeEventQuery(query: EventQuery, base = new URLSearchParams()): string {
  const params = new URLSearchParams(base);
  const set = (key: string, value: string | undefined) =>
    value ? params.set(key, value) : params.delete(key);
  const allTypes = !query.types || query.types.length === EVENT_TYPES.length;
  set("t", allTypes ? undefined : query.types!.join(","));
  const allSeverities = !query.severities || query.severities.length === ALL_SEVERITY_LEVELS.length;
  set("s", allSeverities ? undefined : query.severities!.join(","));
  set("q", query.q);
  set("period", query.period);
  set("sort", query.sort === DEFAULT_SORT ? undefined : query.sort);
  return params.toString().replace(/%2C/gi, ",");
}

export function periodStart(period: Period | undefined, now = Date.now()): string | undefined {
  if (!period) return undefined;
  return new Date(now - Number(period) * 24 * 3600 * 1000).toISOString();
}

/** API filter for a query (sort travels separately) */
export function toEventFilter(query: Omit<EventQuery, "sort"> & { sort?: EventSort }, now = Date.now()): EventFilter {
  const filter: EventFilter = {};
  if (query.types) filter.types = query.types;
  if (query.severities) filter.severities = query.severities;
  if (query.q) filter.q = query.q;
  const startDate = periodStart(query.period, now);
  if (startDate) filter.startDate = startDate;
  return filter;
}

/** The filter part of a query string, to carry from the map to the list and back */
export function sharedFilterQuery(search: string): string {
  const from = new URLSearchParams(search);
  const to = new URLSearchParams();
  for (const key of SHARED_KEYS) {
    const value = from.get(key);
    if (value) to.set(key, value);
  }
  return to.toString().replace(/%2C/gi, ",");
}
