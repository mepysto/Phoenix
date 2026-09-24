import { create, StateCreator } from "zustand";
import { devtools, DevtoolsOptions } from "zustand/middleware";
import { EVENT_TYPES } from "@phoenix/shared/constants";
import {
  APIError,
  eventsAPI,
  type ApiDisasterEvent,
  type EventFilter,
  type EventType,
  type SeverityLevel,
} from "@/lib/api/client";

// Must list every type the API returns, or a partial filter silently hides the rest
export const ALL_EVENT_TYPES: EventType[] = [...EVENT_TYPES];

export const ALL_SEVERITIES: SeverityLevel[] = [
  "low",
  "medium",
  "high",
  "critical",
];

interface EventState {
  events: ApiDisasterEvent[];
  selectedEvent: ApiDisasterEvent | null;
  isLoading: boolean;
  error: string | null;
  filter: EventFilter;
  visibleTypes: Set<EventType>;
  visibleSeverities: Set<SeverityLevel>;
  pagination: {
    total: number;
    limit: number;
    offset: number;
    hasMore: boolean;
  };
}

interface EventActions {
  fetchEvents: () => Promise<void>;
  selectEvent: (event: ApiDisasterEvent | null) => void;
  setFilter: (filter: Partial<EventFilter>) => void;
  toggleEventType: (type: EventType) => void;
  toggleSeverity: (severity: SeverityLevel) => void;
  /** Set visible types/severities at once (undefined = all); does not fetch */
  setVisibility: (types?: EventType[], severities?: SeverityLevel[]) => void;
  clearFilters: () => void;
  /** Apply live change notifications (ids from the WebSocket stream) */
  applyEventChanges: (eventIds: string[]) => Promise<void>;
}

type EventStore = EventState & EventActions;

/** API maximum page size */
const PAGE_SIZE = 200;
/** Safety cap on events held in memory for the map */
export const MAX_EVENTS = 2000;
let latestRequestId = 0;
/** Above this many changed ids, refetch the list instead of each event */
const MAX_INDIVIDUAL_FETCHES = 20;

function matchesVisibleFilters(
  event: ApiDisasterEvent,
  state: Pick<EventState, "visibleTypes" | "visibleSeverities" | "filter">,
): boolean {
  if (!state.visibleTypes.has(event.type as EventType)) return false;
  if (!state.visibleSeverities.has(event.severity as SeverityLevel)) return false;
  if (state.filter.isActive !== undefined && event.isActive !== state.filter.isActive) {
    return false;
  }
  return true;
}

const initialState: EventState = {
  events: [],
  selectedEvent: null,
  isLoading: false,
  error: null,
  filter: {},
  visibleTypes: new Set(ALL_EVENT_TYPES),
  visibleSeverities: new Set(ALL_SEVERITIES),
  pagination: {
    total: 0,
    limit: 50,
    offset: 0,
    hasMore: false,
  },
};

const storeImpl: StateCreator<EventStore, [], []> = (set, get) => ({
  ...initialState,

  fetchEvents: async () => {
    const { visibleTypes, visibleSeverities, filter } = get();
    // Every call supersedes earlier ones: rapid filter toggles must not let a
    // slow, stale response overwrite the result of the latest filter.
    const requestId = ++latestRequestId;
    const isStale = () => requestId !== latestRequestId;

    if (visibleTypes.size === 0 || visibleSeverities.size === 0) {
      set({ events: [], isLoading: false, error: null });
      return;
    }

    set({ isLoading: true, error: null });

    const apiFilter: EventFilter = { ...filter };
    if (visibleTypes.size < ALL_EVENT_TYPES.length) {
      apiFilter.types = Array.from(visibleTypes);
    }
    if (visibleSeverities.size < ALL_SEVERITIES.length) {
      apiFilter.severities = Array.from(visibleSeverities);
    }

    try {
      // The map shows every matching event, not just the first page
      const events: ApiDisasterEvent[] = [];
      let total = 0;
      for (let offset = 0; offset < MAX_EVENTS; offset += PAGE_SIZE) {
        const response = await eventsAPI.list(apiFilter, PAGE_SIZE, offset);
        if (isStale()) return;
        events.push(...response.data);
        total = response.pagination.total;
        if (!response.pagination.hasMore) break;
      }
      set({
        events,
        pagination: {
          total,
          limit: PAGE_SIZE,
          offset: 0,
          hasMore: total > events.length,
        },
        isLoading: false,
      });
    } catch (error) {
      if (isStale()) return;
      set({
        error:
          error instanceof Error ? error.message : "Failed to fetch events",
        isLoading: false,
      });
    }
  },

  selectEvent: (event) => {
    set({ selectedEvent: event });
  },

  setFilter: (newFilter) => {
    set((state) => ({
      filter: { ...state.filter, ...newFilter },
    }));
    get().fetchEvents();
  },

  toggleEventType: (type) => {
    set((state) => {
      const newVisibleTypes = new Set(state.visibleTypes);
      if (newVisibleTypes.has(type)) {
        newVisibleTypes.delete(type);
      } else {
        newVisibleTypes.add(type);
      }
      return { visibleTypes: newVisibleTypes };
    });
    get().fetchEvents();
  },

  setVisibility: (types, severities) => {
    set({
      visibleTypes: new Set(types ?? ALL_EVENT_TYPES),
      visibleSeverities: new Set(severities ?? ALL_SEVERITIES),
    });
  },

  toggleSeverity: (severity) => {
    set((state) => {
      const newVisibleSeverities = new Set(state.visibleSeverities);
      if (newVisibleSeverities.has(severity)) {
        newVisibleSeverities.delete(severity);
      } else {
        newVisibleSeverities.add(severity);
      }
      return { visibleSeverities: newVisibleSeverities };
    });
    get().fetchEvents();
  },

  applyEventChanges: async (eventIds) => {
    const { filter } = get();
    // Live changes describe "now"; a historical view must not change under the user
    if (filter.at) return;
    // Large batches (a full sync) or an active text search: one refresh is
    // cheaper and keeps server-side filtering authoritative.
    if (eventIds.length > MAX_INDIVIDUAL_FETCHES || filter.q) {
      await get().fetchEvents();
      return;
    }
    const results = await Promise.allSettled(eventIds.map((id) => eventsAPI.get(id)));
    set((state) => {
      const byId = new Map(state.events.map((e) => [e.id, e]));
      results.forEach((result, i) => {
        const id = eventIds[i]!;
        if (result.status === "rejected") {
          // 404: deleted upstream; other errors: keep what we have
          if (result.reason instanceof APIError && result.reason.statusCode === 404) byId.delete(id);
          return;
        }
        const event = result.value;
        if (matchesVisibleFilters(event, state)) byId.set(id, event);
        else byId.delete(id); // e.g. severity changed out of the visible set
      });
      const events = [...byId.values()].sort(
        (a, b) => Date.parse(b.startDate) - Date.parse(a.startDate),
      );
      return { events };
    });
  },

  clearFilters: () => {
    set({
      filter: {},
      visibleTypes: new Set(ALL_EVENT_TYPES),
      visibleSeverities: new Set(ALL_SEVERITIES),
    });
    get().fetchEvents();
  },
});

const withDevtools = <T>(
  impl: StateCreator<T, [], []>,
  options: DevtoolsOptions,
): StateCreator<T, [], []> => {
  if (process.env.NODE_ENV === "development") {
    return devtools(impl, options) as unknown as StateCreator<T, [], []>;
  }
  return impl;
};

export const useEventStore = create<EventStore>()(
  withDevtools(storeImpl, { name: "event-store" }),
);

export type {
  ApiDisasterEvent as DisasterEvent,
  EventFilter,
  EventType,
  SeverityLevel,
};
