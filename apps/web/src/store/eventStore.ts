import { create, StateCreator } from "zustand";
import { devtools, DevtoolsOptions } from "zustand/middleware";
import {
  eventsAPI,
  type ApiDisasterEvent,
  type EventFilter,
  type EventType,
  type SeverityLevel,
} from "@/lib/api/client";

interface EventState {
  events: ApiDisasterEvent[];
  selectedEvent: ApiDisasterEvent | null;
  isLoading: boolean;
  error: string | null;
  filter: EventFilter;
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
    const { filter, pagination } = get();
    set({ isLoading: true, error: null });

    try {
      const response = await eventsAPI.list(filter, pagination.limit, 0);
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
      const currentTypes = state.filter.types || [];
      const newTypes = currentTypes.includes(type)
        ? currentTypes.filter((t) => t !== type)
        : [...currentTypes, type];
      return {
        filter: {
          ...state.filter,
          types: newTypes.length > 0 ? newTypes : undefined,
        },
      };
    });
    get().fetchEvents();
  },

  toggleSeverity: (severity) => {
    set((state) => {
      const currentSeverities = state.filter.severities || [];
      const newSeverities = currentSeverities.includes(severity)
        ? currentSeverities.filter((s) => s !== severity)
        : [...currentSeverities, severity];
      return {
        filter: {
          ...state.filter,
          severities: newSeverities.length > 0 ? newSeverities : undefined,
        },
      };
    });
    get().fetchEvents();
  },

  clearFilters: () => {
    set({ filter: {} });
    get().fetchEvents();
  },

  loadMore: async () => {
    const { filter, pagination, events } = get();
    if (!pagination.hasMore) return;

    set({ isLoading: true });
    try {
      const newOffset = pagination.offset + pagination.limit;
      const response = await eventsAPI.list(
        filter,
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
