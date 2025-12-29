import { create, StateCreator } from "zustand";
import { devtools, DevtoolsOptions } from "zustand/middleware";
import {
  eventsAPI,
  type ApiDisasterEvent,
  type EventFilter,
  type EventType,
  type SeverityLevel,
} from "@/lib/api/client";

export const ALL_EVENT_TYPES: EventType[] = [
  "earthquake",
  "flood",
  "wildfire",
  "hurricane",
  "tsunami",
  "volcano",
  "war",
  "pollution",
  "drought",
  "other",
];

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
  loadMore: () => Promise<void>;
}

type EventStore = EventState & EventActions;

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
    const { visibleTypes, visibleSeverities, filter, pagination } = get();

    if (visibleTypes.size === 0 || visibleSeverities.size === 0) {
      set({ events: [], isLoading: false });
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
      const response = await eventsAPI.list(apiFilter, pagination.limit, 0);
      set({
        events: response.data,
        pagination: {
          ...response.pagination,
          offset: 0,
        },
        isLoading: false,
      });
    } catch (error) {
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

  loadMore: async () => {
    const { visibleTypes, visibleSeverities, filter, pagination, events } =
      get();
    if (!pagination.hasMore) return;

    set({ isLoading: true });

    const apiFilter: EventFilter = { ...filter };
    if (visibleTypes.size < ALL_EVENT_TYPES.length) {
      apiFilter.types = Array.from(visibleTypes);
    }
    if (visibleSeverities.size < ALL_SEVERITIES.length) {
      apiFilter.severities = Array.from(visibleSeverities);
    }

    try {
      const newOffset = pagination.offset + pagination.limit;
      const response = await eventsAPI.list(
        apiFilter,
        pagination.limit,
        newOffset,
      );
      set({
        events: [...events, ...response.data],
        pagination: {
          ...response.pagination,
          offset: newOffset,
        },
        isLoading: false,
      });
    } catch (error) {
      set({
        error:
          error instanceof Error ? error.message : "Failed to load more events",
        isLoading: false,
      });
    }
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
