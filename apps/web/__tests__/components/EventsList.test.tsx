import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const nav = vi.hoisted(() => ({ replace: vi.fn(), push: vi.fn(), search: "" }));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: nav.replace, push: nav.push, prefetch: vi.fn() }),
  usePathname: () => "/events",
  useSearchParams: () => new URLSearchParams(nav.search),
}));
vi.mock("@/components/layout/Header", () => ({ Header: () => null }));
vi.mock("@/lib/api/client", async (orig) => ({
  ...(await orig<typeof import("@/lib/api/client")>()),
  eventsAPI: { list: vi.fn(), facets: vi.fn() },
}));

import EventsPage from "@/app/events/page";
import { usefulDescription } from "@/components/events/EventRow";
import { withSharedFilters } from "@/components/layout/nav";
import { eventsAPI, type ApiDisasterEvent } from "@/lib/api/client";
import { useSettingsStore } from "@/store/settingsStore";

const event = (over: Partial<ApiDisasterEvent>) =>
  ({
    id: "e1",
    type: "flood",
    title: "Flood in Mozambique",
    description: "The Flood notification level is Red.",
    severity: "critical",
    isActive: true,
    startDate: new Date().toISOString(),
    affectedPopulation: 120000,
    location: { lat: -24, lng: 33, country: "Mozambique", countryCode: "MOZ", region: null },
    displayPoint: { lat: -24, lng: 33, source: "event" },
    ...over,
  }) as unknown as ApiDisasterEvent;

describe("Disaster list", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    nav.search = "";
    useSettingsStore.getState().setLanguage("en");
    vi.mocked(eventsAPI.list).mockResolvedValue({
      data: [event({}), event({ id: "e2", type: "earthquake", severity: "medium", title: "M 4.7 - 54 km NW of Lebu, Chile", description: "Magnitude 4.7. Location: 54 km NW of Lebu, Chile.", affectedPopulation: null, location: { lat: -37, lng: -74, country: null, countryCode: null, region: null } as never })],
      pagination: { total: 120, limit: 50, offset: 0, hasMore: true },
    } as never);
    vi.mocked(eventsAPI.facets).mockResolvedValue({
      total: 120,
      byType: { earthquake: 100, flood: 20 },
      bySeverity: { critical: 3, medium: 117 },
    });
  });

  it("asks for the most important events first and says how many are shown", async () => {
    render(<EventsPage />);

    expect(await screen.findByText("Flood in Mozambique")).toBeInTheDocument();
    expect(eventsAPI.list).toHaveBeenCalledWith({}, 50, 0, "importance");
    expect(screen.getByText("2 of 120")).toBeInTheDocument();
    // A place name, not coordinates; USGS rows take it from the title
    expect(screen.getByText("Mozambique")).toBeInTheDocument();
    expect(screen.getByText("Lebu, Chile")).toBeInTheDocument();
    // People affected, shortened; nothing (not "0") when unknown
    expect(screen.getByText("120K")).toBeInTheDocument();
  });

  it("shows counts on chips and folds away types without events", async () => {
    render(<EventsPage />);
    const types = await screen.findByRole("group", { name: "Event types" });

    await waitFor(() => expect(within(types).getByRole("button", { name: /Earthquake/ })).toHaveTextContent("100"));
    expect(within(types).queryByRole("button", { name: /Tsunami/ })).not.toBeInTheDocument();
    fireEvent.click(within(types).getByRole("button", { name: /15 more types/ }));
    expect(within(types).getByRole("button", { name: /Tsunami/ })).toHaveTextContent("0");
  });

  it("keeps filters in the URL", async () => {
    render(<EventsPage />);
    const severity = await screen.findByRole("group", { name: "Severity" });

    fireEvent.click(within(severity).getByRole("button", { name: /Critical/ }));
    expect(nav.replace).toHaveBeenCalledWith("/events?s=critical", { scroll: false });

    fireEvent.change(screen.getByLabelText("Sort"), { target: { value: "recent" } });
    expect(nav.replace).toHaveBeenLastCalledWith("/events?sort=recent", { scroll: false });
  });

  it("reads filters from the URL and passes them to the map link", async () => {
    nav.search = "t=flood&s=high,critical&period=7&sort=recent";
    render(<EventsPage />);

    await screen.findByText("Flood in Mozambique");
    const [filter, , , sort] = vi.mocked(eventsAPI.list).mock.calls[0]!;
    expect(filter).toMatchObject({ types: ["flood"], severities: ["high", "critical"] });
    expect(filter?.startDate).toBeDefined();
    expect(sort).toBe("recent");
    expect(screen.getByRole("link", { name: "View on Map" })).toHaveAttribute(
      "href",
      "/?t=flood&s=high,critical&period=7",
    );
  });
});

describe("helpers", () => {
  it("drops descriptions that only repeat the title or place", () => {
    expect(usefulDescription(event({ description: "Magnitude 4.7. Location: Lebu, Chile." }), "Lebu, Chile")).toBeNull();
    expect(usefulDescription(event({ description: "No description available" }), "x")).toBeNull();
    expect(usefulDescription(event({}), "Mozambique")).toBe("The Flood notification level is Red.");
  });

  it("carries filters only between the map and the list", () => {
    expect(withSharedFilters("/events", "/", "?t=flood&v=1,2,3")).toBe("/events?t=flood");
    expect(withSharedFilters("/", "/events", "?s=high&sort=recent")).toBe("/?s=high");
    expect(withSharedFilters("/dashboard", "/", "?t=flood")).toBe("/dashboard");
    expect(withSharedFilters("/events", "/plan", "?t=flood")).toBe("/events");
  });
});
