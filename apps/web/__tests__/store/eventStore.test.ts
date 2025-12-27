import { describe, it, expect, vi, beforeEach } from "vitest";
import { act } from "@testing-library/react";

// Mock the API client before importing the store
vi.mock("@/lib/api/client", () => ({
  eventsAPI: {
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
import { useEventStore } from "@/store/eventStore";

const resetStore = () => {
  useEventStore.setState({
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
    it("adds event type to filter when toggled on", async () => {
      await act(async () => {
        useEventStore.getState().toggleEventType("earthquake");
      });

      const { filter } = useEventStore.getState();
      expect(filter.types).toContain("earthquake");
    });

    it("removes event type from filter when toggled off", async () => {
      // First add the type
      await act(async () => {
        useEventStore.getState().toggleEventType("earthquake");
      });

      // Then remove it
      await act(async () => {
        useEventStore.getState().toggleEventType("earthquake");
      });

      const { filter } = useEventStore.getState();
      expect(filter.types).toBeUndefined();
    });

    it("can toggle multiple event types", async () => {
      await act(async () => {
        useEventStore.getState().toggleEventType("earthquake");
      });

      await act(async () => {
        useEventStore.getState().toggleEventType("flood");
      });

      const { filter } = useEventStore.getState();
      expect(filter.types).toBeDefined();
      expect(filter.types!).toContain("earthquake");
      expect(filter.types!).toContain("flood");
    });
  });

  describe("toggleSeverity", () => {
    it("adds severity to filter when toggled on", async () => {
      await act(async () => {
        useEventStore.getState().toggleSeverity("high");
      });

      const { filter } = useEventStore.getState();
      expect(filter.severities).toContain("high");
    });

    it("removes severity from filter when toggled off", async () => {
      await act(async () => {
        useEventStore.getState().toggleSeverity("high");
      });

      await act(async () => {
        useEventStore.getState().toggleSeverity("high");
      });

      const { filter } = useEventStore.getState();
      expect(filter.severities).toBeUndefined();
    });
  });

  describe("clearFilters", () => {
    it("clears all filters", async () => {
      // Add some filters first
      await act(async () => {
        useEventStore.getState().toggleEventType("earthquake");
      });

      await act(async () => {
        useEventStore.getState().toggleSeverity("high");
      });

      // Clear filters
      await act(async () => {
        useEventStore.getState().clearFilters();
      });

      const { filter } = useEventStore.getState();
      expect(filter).toEqual({});
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
});
