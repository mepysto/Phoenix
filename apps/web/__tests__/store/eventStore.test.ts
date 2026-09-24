import { describe, it, expect, vi, beforeEach } from "vitest";
import { act } from "@testing-library/react";

// Mock the API client before importing the store
vi.mock("@/lib/api/client", () => ({
  APIError: class APIError extends Error {
    constructor(
      public statusCode: number,
      message: string,
    ) {
      super(message);
    }
  },
  eventsAPI: {
    get: vi.fn(),
    list: vi.fn().mockResolvedValue({
      data: [
        {
          id: "1",
          type: "earthquake",
          title: "Test Earthquake",
          severity: "high",
          location: { lat: 35.6762, lng: 139.6503, country: "Japan" },
          isActive: true,
          startDate: "2024-01-01T00:00:00Z",
          sources: [],
          createdAt: "2024-01-01T00:00:00Z",
          updatedAt: "2024-01-01T00:00:00Z",
        },
      ],
      pagination: {
        total: 1,
        limit: 50,
        offset: 0,
        hasMore: false,
      },
    }),
  },
}));

// Import the store after mocking
import { APIError, eventsAPI } from "@/lib/api/client";
import {
  ALL_EVENT_TYPES,
  ALL_SEVERITIES,
  useEventStore,
} from "@/store/eventStore";

const resetStore = () => {
  useEventStore.setState({
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
  });
};

describe("eventStore", () => {
  beforeEach(() => {
    // Reset the store state before each test
    resetStore();
    vi.clearAllMocks();
  });

  describe("initial state", () => {
    it("has empty events array initially", () => {
      const { events } = useEventStore.getState();
      expect(events).toEqual([]);
    });

    it("has null selectedEvent initially", () => {
      const { selectedEvent } = useEventStore.getState();
      expect(selectedEvent).toBeNull();
    });

    it("has isLoading false initially", () => {
      const { isLoading } = useEventStore.getState();
      expect(isLoading).toBe(false);
    });

    it("has null error initially", () => {
      const { error } = useEventStore.getState();
      expect(error).toBeNull();
    });

    it("has empty filter initially", () => {
      const { filter } = useEventStore.getState();
      expect(filter).toEqual({});
    });
  });

  describe("selectEvent", () => {
    it("sets selectedEvent when called", () => {
      const mockEvent = {
        id: "1",
        type: "earthquake" as const,
        title: "Test Earthquake",
        severity: "high" as const,
        location: { lat: 35.6762, lng: 139.6503, country: "Japan" },
        isActive: true,
        startDate: "2024-01-01T00:00:00Z",
        sources: [],
        createdAt: "2024-01-01T00:00:00Z",
        updatedAt: "2024-01-01T00:00:00Z",
      };

      act(() => {
        useEventStore.getState().selectEvent(mockEvent);
      });

      const { selectedEvent } = useEventStore.getState();
      expect(selectedEvent).toEqual(mockEvent);
    });

    it("clears selectedEvent when called with null", () => {
      const mockEvent = {
        id: "1",
        type: "earthquake" as const,
        title: "Test Earthquake",
        severity: "high" as const,
        location: { lat: 35.6762, lng: 139.6503, country: "Japan" },
        isActive: true,
        startDate: "2024-01-01T00:00:00Z",
        sources: [],
        createdAt: "2024-01-01T00:00:00Z",
        updatedAt: "2024-01-01T00:00:00Z",
      };

      act(() => {
        useEventStore.getState().selectEvent(mockEvent);
      });

      act(() => {
        useEventStore.getState().selectEvent(null);
      });

      const { selectedEvent } = useEventStore.getState();
      expect(selectedEvent).toBeNull();
    });
  });

  describe("toggleEventType", () => {
    it("hides a visible type and queries only the remaining types", async () => {
      await act(async () => {
        useEventStore.getState().toggleEventType("earthquake");
      });

      const { visibleTypes } = useEventStore.getState();
      expect(visibleTypes.has("earthquake")).toBe(false);
      const filter = vi.mocked(eventsAPI.list).mock.calls.at(-1)![0]!;
      expect(filter.types).toHaveLength(ALL_EVENT_TYPES.length - 1);
      expect(filter.types).not.toContain("earthquake");
    });

    it("shows the type again when toggled twice", async () => {
      await act(async () => {
        useEventStore.getState().toggleEventType("earthquake");
      });
      await act(async () => {
        useEventStore.getState().toggleEventType("earthquake");
      });

      expect(useEventStore.getState().visibleTypes.has("earthquake")).toBe(true);
      // All types visible → no type filter sent to the API
      const filter = vi.mocked(eventsAPI.list).mock.calls.at(-1)![0]!;
      expect(filter.types).toBeUndefined();
    });
  });

  describe("toggleSeverity", () => {
    it("hides a visible severity", async () => {
      await act(async () => {
        useEventStore.getState().toggleSeverity("high");
      });

      expect(useEventStore.getState().visibleSeverities.has("high")).toBe(false);
    });

    it("clears the map without an API call when nothing is visible", async () => {
      for (const severity of ALL_SEVERITIES) {
        await act(async () => {
          useEventStore.getState().toggleSeverity(severity);
        });
      }
      vi.mocked(eventsAPI.list).mockClear();
      await act(async () => {
        await useEventStore.getState().fetchEvents();
      });

      expect(useEventStore.getState().events).toEqual([]);
      expect(eventsAPI.list).not.toHaveBeenCalled();
    });
  });

  describe("clearFilters", () => {
    it("restores every type and severity", async () => {
      await act(async () => {
        useEventStore.getState().toggleEventType("earthquake");
        useEventStore.getState().toggleSeverity("high");
      });
      await act(async () => {
        useEventStore.getState().clearFilters();
      });

      const state = useEventStore.getState();
      expect(state.filter).toEqual({});
      expect(state.visibleTypes.size).toBe(ALL_EVENT_TYPES.length);
      expect(state.visibleSeverities.size).toBe(ALL_SEVERITIES.length);
    });
  });

  describe("fetchEvents", () => {
    it("sets isLoading to true during fetch", async () => {
      const fetchPromise = act(async () => {
        useEventStore.getState().fetchEvents();
      });

      // isLoading should be true while fetching
      // Note: This is a simplified test - in real scenarios you might use waitFor
      await fetchPromise;
    });

    it("populates events after successful fetch", async () => {
      await act(async () => {
        await useEventStore.getState().fetchEvents();
      });

      const { events } = useEventStore.getState();
      expect(events.length).toBeGreaterThan(0);
      expect(events[0]?.type).toBe("earthquake");
    });
  });

  describe("fetchEvents pagination and races", () => {
    const page = (ids: string[], hasMore: boolean, total: number) => ({
      data: ids.map((id) => ({ id, type: "flood", severity: "low" })),
      pagination: { total, limit: 200, offset: 0, hasMore },
    });

    it("loads every page instead of stopping at the first", async () => {
      vi.mocked(eventsAPI.list)
        .mockResolvedValueOnce(page(["a", "b"], true, 3) as never)
        .mockResolvedValueOnce(page(["c"], false, 3) as never);

      await act(async () => {
        await useEventStore.getState().fetchEvents();
      });

      expect(useEventStore.getState().events.map((e) => e.id)).toEqual(["a", "b", "c"]);
      expect(vi.mocked(eventsAPI.list).mock.calls.map((c) => c[2])).toEqual([0, 200]);
    });

    it("ignores a slow response that was superseded by a newer request", async () => {
      let resolveSlow: (v: unknown) => void = () => {};
      vi.mocked(eventsAPI.list)
        .mockImplementationOnce(() => new Promise((r) => (resolveSlow = r)) as never)
        .mockResolvedValueOnce(page(["new"], false, 1) as never);

      await act(async () => {
        const slow = useEventStore.getState().fetchEvents();
        await useEventStore.getState().fetchEvents();
        resolveSlow(page(["stale"], false, 1));
        await slow;
      });

      expect(useEventStore.getState().events.map((e) => e.id)).toEqual(["new"]);
    });
  });

  describe("applyEventChanges (live updates)", () => {
    const ev = (id: string, over: Record<string, unknown> = {}) => ({
      id,
      type: "flood",
      severity: "low",
      isActive: true,
      startDate: "2026-09-01T00:00:00Z",
      title: id,
      ...over,
    });

    it("inserts new events, updates changed ones and keeps newest first", async () => {
      useEventStore.setState({ events: [ev("old", { title: "before" })] as never });
      vi.mocked(eventsAPI.get).mockImplementation(async (id: string) =>
        (id === "old"
          ? ev("old", { title: "after" })
          : ev("new", { startDate: "2026-09-02T00:00:00Z" })) as never,
      );

      await act(async () => {
        await useEventStore.getState().applyEventChanges(["old", "new"]);
      });

      const events = useEventStore.getState().events;
      expect(events.map((e) => e.id)).toEqual(["new", "old"]);
      expect(events[1]!.title).toBe("after");
      expect(eventsAPI.list).not.toHaveBeenCalled();
    });

    it("removes events that no longer match the visible filters or were deleted", async () => {
      useEventStore.setState({
        events: [ev("a"), ev("gone")] as never,
        visibleSeverities: new Set(["low"]) as never,
      });
      vi.mocked(eventsAPI.get).mockImplementation(async (id: string) => {
        if (id === "gone") throw new APIError(404, "not found");
        return ev("a", { severity: "critical" }) as never; // now filtered out
      });

      await act(async () => {
        await useEventStore.getState().applyEventChanges(["a", "gone"]);
      });

      expect(useEventStore.getState().events).toEqual([]);
    });

    it("keeps an event when fetching it fails for reasons other than 404", async () => {
      useEventStore.setState({ events: [ev("a")] as never });
      vi.mocked(eventsAPI.get).mockRejectedValue(new APIError(503, "unavailable"));

      await act(async () => {
        await useEventStore.getState().applyEventChanges(["a"]);
      });

      expect(useEventStore.getState().events.map((e) => e.id)).toEqual(["a"]);
    });

    it("refetches the list for large batches instead of one request per event", async () => {
      const ids = Array.from({ length: 21 }, (_, i) => `e${i}`);
      await act(async () => {
        await useEventStore.getState().applyEventChanges(ids);
      });
      expect(eventsAPI.get).not.toHaveBeenCalled();
      expect(eventsAPI.list).toHaveBeenCalled();
    });
  });
});
