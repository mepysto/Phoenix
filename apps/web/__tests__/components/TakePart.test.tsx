import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const nav = vi.hoisted(() => ({ search: "" }));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), prefetch: vi.fn() }),
  usePathname: () => "/act",
  useSearchParams: () => new URLSearchParams(nav.search),
}));
vi.mock("@/components/layout/Header", () => ({ Header: () => null }));
// The map picker stands in as a button that picks a fixed point
vi.mock("next/dynamic", () => ({
  default: () =>
    function FakeMap({ onPick }: { onPick?: (lat: number, lng: number) => void }) {
      return onPick ? (
        <button type="button" onClick={() => onPick(37.57, 126.98)}>
          fake map
        </button>
      ) : null;
    },
}));
vi.mock("@/lib/api/client", async (orig) => ({
  ...(await orig<typeof import("@/lib/api/client")>()),
  eventsAPI: { list: vi.fn(), get: vi.fn() },
}));
vi.mock("@/lib/api/community", async (orig) => ({
  ...(await orig<typeof import("@/lib/api/community")>()),
  communityAPI: { needs: vi.fn() },
  plansAPI: { list: vi.fn() },
  challengesAPI: { list: vi.fn() },
}));

import ActPage from "@/app/act/page";
import AlertsPage from "@/app/alerts/page";
import { circlePolygon } from "@/components/alerts/AreaPickerMap";
import { eventsAPI } from "@/lib/api/client";
import { challengesAPI, communityAPI, plansAPI } from "@/lib/api/community";
import { useSettingsStore } from "@/store/settingsStore";

const event = (id: string, title: string, severity = "high") =>
  ({
    id,
    title,
    type: "flood",
    severity,
    isActive: true,
    startDate: new Date().toISOString(),
    location: { lat: 1, lng: 2, country: "Chad", countryCode: "TCD", region: null },
    displayPoint: { lat: 1, lng: 2, source: "event" },
  }) as never;

describe("Take part", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useSettingsStore.getState().setLanguage("en");
    vi.mocked(communityAPI.needs).mockResolvedValue({
      data: [{ eventId: "asked" }, { eventId: "asked" }, { eventId: null }] as never,
      total: 3,
    });
    vi.mocked(plansAPI.list).mockResolvedValue({ data: [{}, {}] } as never);
    vi.mocked(challengesAPI.list).mockResolvedValue({ data: [{ isOpen: true }, { isOpen: false }] } as never);
    vi.mocked(eventsAPI.get).mockResolvedValue(event("asked", "Flood in Chad"));
    vi.mocked(eventsAPI.list).mockResolvedValue({ data: [event("asked", "Flood in Chad"), event("severe", "Cyclone", "critical")] } as never);
  });

  it("shows the three ways to help with live counts", async () => {
    render(<ActPage />);
    expect(await screen.findByText("3 open needs")).toBeInTheDocument();
    expect(screen.getByText("2 site plans")).toBeInTheDocument();
    expect(screen.getByText("1 open challenges")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Needs and offers/ })).toHaveAttribute("href", "/connect");
  });

  it("lists disasters with needs first, then severe ones, each opening its help tab", async () => {
    render(<ActPage />);
    const list = await screen.findByRole("region", { name: "Disasters that need help" });
    await waitFor(() => expect(within(list).getAllByRole("link")).toHaveLength(2));
    const links = within(list).getAllByRole("link");
    expect(links[0]).toHaveTextContent("Flood in Chad");
    expect(links[0]).toHaveTextContent("2 needs");
    expect(links[0]).toHaveAttribute("href", "/events/asked?tab=help");
    expect(links[1]).toHaveTextContent("Cyclone");
  });
});

describe("Area alerts", () => {
  beforeEach(() => {
    localStorage.clear();
    nav.search = "";
    useSettingsStore.getState().setLanguage("en");
  });

  it("adds an area by picking on the map, without typing coordinates", () => {
    render(<AlertsPage />);
    expect(screen.getByText("Choose a place first")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "fake map" }));
    expect(screen.getByText("Centre: 37.57, 126.98")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Name"), { target: { value: "Seoul" } });
    fireEvent.click(screen.getByRole("button", { name: "Save area" }));

    expect(screen.getByText("Seoul")).toBeInTheDocument();
  });

  it("draws the radius as a closed circle", () => {
    const ring = circlePolygon(0, 0, 100).geometry.coordinates[0]!;
    expect(ring[0]).toEqual(ring[ring.length - 1]);
    // 100 km north of the equator is about 0.9 degrees
    expect(Math.max(...ring.map((point) => point[1]!))).toBeCloseTo(0.899, 2);
  });
});
