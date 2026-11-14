import { fireEvent, render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/components/map/SatellitePasses", () => ({ SatellitePasses: () => null }));
vi.mock("@/components/map/NearbyCameras", () => ({ NearbyCameras: () => null }));
vi.mock("@/components/map/LocalRadio", () => ({ LocalRadio: () => null }));

import { EventInfoPanel } from "@/components/map/EventInfoPanel";
import type { ApiDisasterEvent } from "@/lib/api/client";
import { eventsInView } from "@/lib/map/inView";
import { useSettingsStore } from "@/store/settingsStore";
import { useUiStore } from "@/store/uiStore";

const event = (over: Partial<ApiDisasterEvent> = {}) =>
  ({
    id: "e1",
    type: "flood",
    title: "Flood in Mozambique",
    description: "Long description that the summary should not lead with.",
    severity: "critical",
    isActive: true,
    startDate: new Date(Date.now() - 3 * 3600_000).toISOString(),
    affectedPopulation: 120000,
    location: { lat: -24, lng: 33, country: "Mozambique", countryCode: "MOZ", region: null },
    displayPoint: { lat: -24, lng: 33, source: "event" },
    trust: { confidence: 60, band: "medium", sourceCount: 1, lifecycle: "responding", reasons: [] },
    ...over,
  }) as unknown as ApiDisasterEvent;

describe("Event summary on the map", () => {
  beforeEach(() => useSettingsStore.getState().setLanguage("en"));

  it("leads with place, time and people, and makes 'View details' the main action", () => {
    render(<EventInfoPanel event={event()} onClose={vi.fn()} />);
    const panel = screen.getByRole("region", { name: "Flood in Mozambique" });

    expect(within(panel).getByText("Mozambique")).toBeInTheDocument();
    expect(within(panel).getByText(/3 hours ago · .* UTC/)).toBeInTheDocument();
    expect(within(panel).getByText("120,000 affected")).toBeInTheDocument();

    const links = within(panel).getAllByRole("link");
    expect(links[0]).toHaveTextContent("View details");
    expect(links[0]).toHaveAttribute("href", "/events/e1");
    expect(links[0]).toHaveClass("btn-primary");
    expect(links.map((a) => a.textContent)).toEqual(["View details", "Offer help", "Watch this area"]);
    expect(links[2]).toHaveAttribute("href", expect.stringContaining("/alerts?lat=-24.00&lng=33.00&name=Mozambique"));
  });

  it("folds confidence, the brief and nearby tools away", () => {
    render(<EventInfoPanel event={event()} onClose={vi.fn()} />);
    const more = screen.getByText("Confidence, brief and nearby").closest("details")!;
    expect(more).not.toHaveAttribute("open");
    fireEvent.click(screen.getByText("Confidence, brief and nearby"));
    expect(more).toHaveAttribute("open");
  });
});

describe("Right-hand panel", () => {
  it("holds one thing at a time", () => {
    useUiStore.getState().setRightPanel("assistant");
    useUiStore.getState().setRightPanel("in-view");
    expect(useUiStore.getState().rightPanel).toBe("in-view");
  });

  it("lists active events in view, most severe first, then newest", () => {
    const now = Date.now();
    const at = (id: string, severity: string, lng: number, hoursAgo: number, isActive = true) =>
      event({ id, severity, isActive, startDate: new Date(now - hoursAgo * 3600_000).toISOString(), location: { lat: 0, lng } as never, displayPoint: { lat: 0, lng, source: "event" } as never });
    const list = eventsInView(
      [at("low", "low", 10, 1), at("crit-old", "critical", 10, 50), at("crit-new", "critical", 10, 2), at("ended", "critical", 10, 1, false), at("outside", "critical", 100, 1)],
      [0, -10, 20, 10],
    );
    expect(list.map((e) => e.id)).toEqual(["crit-new", "crit-old", "low"]);
  });

  it("handles a view across the antimeridian", () => {
    const fiji = event({ id: "fiji", location: { lat: -17, lng: 178 } as never, displayPoint: { lat: -17, lng: 178, source: "event" } as never });
    expect(eventsInView([fiji], [170, -30, -170, 0]).map((e) => e.id)).toEqual(["fiji"]);
  });
});
