import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const nav = vi.hoisted(() => ({ search: "" }));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), prefetch: vi.fn() }),
  usePathname: () => "/plan",
  useSearchParams: () => new URLSearchParams(nav.search),
}));
vi.mock("next/dynamic", () => ({ default: () => () => null }));
vi.mock("@/components/layout/Header", () => ({ Header: () => null }));
vi.mock("@/components/plan/PlanSaveBar", () => ({ PlanSaveBar: () => null }));
vi.mock("@/lib/api/client", async (orig) => ({
  ...(await orig<typeof import("@/lib/api/client")>()),
  eventsAPI: { list: vi.fn(), get: vi.fn() },
}));

import PlanPage from "@/app/plan/page";
import { eventsAPI } from "@/lib/api/client";
import { useSettingsStore } from "@/store/settingsStore";

const flood = {
  id: "ev1",
  title: "Flood in Chad",
  type: "flood",
  severity: "high",
  isActive: true,
  startDate: new Date().toISOString(),
  affectedPopulation: null,
  location: { lat: 12, lng: 15, country: "Chad", countryCode: "TCD", region: null },
  displayPoint: { lat: 12, lng: 15, source: "event" },
} as never;

describe("Site planner", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useSettingsStore.getState().setLanguage("en");
    window.history.replaceState(null, "", "/plan");
    vi.mocked(eventsAPI.list).mockResolvedValue({ data: [flood] } as never);
    vi.mocked(eventsAPI.get).mockResolvedValue(flood);
  });

  it("asks which disaster the site is for before showing a map", async () => {
    nav.search = "";
    render(<PlanPage />);
    expect(screen.getByRole("heading", { name: "Which disaster is this site for?" })).toBeInTheDocument();
    expect(await screen.findByRole("link", { name: /Flood in Chad/ })).toHaveAttribute("href", "/plan?event=ev1");
    expect(screen.getByRole("button", { name: "Start on an empty map" })).toBeInTheDocument();
  });

  it("opens on the chosen disaster and names it over the map", async () => {
    nav.search = "event=ev1";
    render(<PlanPage />);
    const context = await screen.findByRole("link", { name: /Site plan for/ });
    expect(context).toHaveTextContent("Site plan for · Flood in Chad");
    expect(context).toHaveAttribute("href", "/events/ev1");
  });

  it("reads 'not started' rather than failing before anything is placed", async () => {
    nav.search = "event=ev1";
    render(<PlanPage />);
    await screen.findByRole("link", { name: /Site plan for/ });
    expect(screen.getAllByText("Not started").length).toBeGreaterThan(5);
    expect(screen.queryByText("Short")).not.toBeInTheDocument();
  });
});
