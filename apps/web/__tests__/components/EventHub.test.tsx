import { fireEvent, render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const hub = vi.hoisted(() => ({ value: {} as Record<string, unknown> }));
vi.mock("next/navigation", () => ({
  useParams: () => ({ id: "e1" }),
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), prefetch: vi.fn() }),
  usePathname: () => "/events/e1",
  useSearchParams: () => new URLSearchParams(),
}));
vi.mock("next/dynamic", () => ({ default: () => () => null }));
vi.mock("@/components/layout/Header", () => ({ Header: () => null }));
vi.mock("@/components/event/SitrepPanel", () => ({ SitrepPanel: () => null }));
vi.mock("@/hooks/useEventHub", () => ({ useEventHub: () => hub.value }));

import EventDetailPage from "@/app/events/[id]/page";
import { dayOfEvent } from "@/components/event/hub/EventHeader";
import { useSettingsStore } from "@/store/settingsStore";

const HOUR = 3600_000;
const baseEvent = {
  id: "e1",
  type: "flood",
  title: "Flood in Mozambique",
  description: null,
  severity: "critical",
  isActive: true,
  startDate: new Date(Date.now() - 30 * HOUR).toISOString(),
  updatedAt: new Date().toISOString(),
  affectedPopulation: null,
  affectedAreaKm2: null,
  location: { lat: -24, lng: 33, country: "Mozambique", countryCode: "MOZ", region: null },
  displayPoint: { lat: -24, lng: 33, source: "event" },
  trust: { confidence: 0.6, band: "medium", sourceCount: 1, lifecycle: "responding", reasons: [] },
  sources: [{ id: "s1", name: "GDACS", type: "disaster_alert" }],
};

function setHub(over: Record<string, unknown> = {}) {
  hub.value = {
    event: baseEvent,
    loading: false,
    errorStatus: null,
    damage: null,
    damageFailed: false,
    needs: [],
    needsTotal: 0,
    plans: [],
    challenges: [],
    updates: [{ id: "u1" }, { id: "u2" }],
    addUpdate: vi.fn(),
    ...over,
  };
}

describe("Event page hub", () => {
  beforeEach(() => {
    useSettingsStore.getState().setLanguage("en");
    window.history.replaceState(null, "", "/events/e1");
    setHub();
  });

  it("puts the ways to act next to the title", () => {
    render(<EventDetailPage />);
    const actions = screen.getAllByRole("navigation", { name: "Actions" })[0]!;
    const hrefs = within(actions).getAllByRole("link").map((a) => [a.textContent, a.getAttribute("href")]);
    expect(hrefs[0]).toEqual(["Offer help", "/connect?event=e1"]);
    expect(hrefs[1]).toEqual(["Site planner", "/plan?event=e1"]);
    expect(within(actions).getByRole("button", { name: "Share" })).toBeInTheDocument();
    expect(screen.getByText("Mozambique · began " + new Date(baseEvent.startDate).toLocaleDateString("en", { dateStyle: "medium" }) + " · day 2")).toBeInTheDocument();
  });

  it("shows four figures, saying 'not yet counted' rather than 0", () => {
    render(<EventDetailPage />);
    expect(screen.getAllByText("Not yet counted")).toHaveLength(2);
    expect(screen.getByRole("button", { name: /Confidence 60% · 1 source/ })).toBeInTheDocument();
  });

  it("lists what is missing in one place instead of empty cards", () => {
    render(<EventDetailPage />);
    const missing = screen.getByRole("region", { name: "Not available yet" });
    expect(within(missing).getByText(/Damage assessment/)).toBeInTheDocument();
    // Onset 30 hours ago: no imagery after it yet
    expect(within(missing).getByText(/Before and after imagery/)).toBeInTheDocument();
  });

  it("counts what each tab holds and explains how help works when there are no needs", () => {
    render(<EventDetailPage />);
    expect(screen.getByRole("tab", { name: "Updates (2)" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("tab", { name: "Needs and help" }));
    expect(screen.getByText("An approved organisation on the ground posts what it needs.")).toBeInTheDocument();
    expect(window.location.search).toBe("?tab=help");
  });

  it("knows which day of the disaster it is", () => {
    const now = Date.parse("2026-11-14T12:00:00Z");
    expect(dayOfEvent("2026-11-14T03:00:00Z", now)).toBe(1);
    expect(dayOfEvent("2026-11-12T13:00:00Z", now)).toBe(2);
  });
});
