import { create, StateCreator } from "zustand";
import { devtools, DevtoolsOptions } from "zustand/middleware";
import { EVENT_TYPES } from "@phoenix/shared/constants";
import {
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
  clearFilters: () => void;
}

type EventStore = EventState & EventActions;

/** API maximum page size */
const PAGE_SIZE = 200;
/** Safety cap on events held in memory for the map */
export const MAX_EVENTS = 2000;
let latestRequestId = 0;

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
