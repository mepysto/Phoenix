import { act, fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { MapControls } from "@/components/map/MapControls";
import { MapLegend } from "@/components/map/MapLegend";
import { MobileViewBar } from "@/components/map/MobileViewBar";
import type { ApiDisasterEvent } from "@/lib/api/client";
import { useEventStore } from "@/store/eventStore";
import { useMapStore } from "@/store/mapStore";
import { useSettingsStore } from "@/store/settingsStore";
import { useUiStore } from "@/store/uiStore";

const event = (id: string, severity: string, lng: number) =>
  ({
    id,
    type: "flood",
    title: id,
    severity,
    isActive: true,
    startDate: new Date().toISOString(),
    location: { lat: 0, lng, country: null, countryCode: null, region: null },
    displayPoint: { lat: 0, lng, source: "event" },
  }) as unknown as ApiDisasterEvent;

describe("Map on phones", () => {
  beforeEach(() => {
    useSettingsStore.getState().setLanguage("en");
    useUiStore.setState({ rightPanel: null, phoneOverlay: null });
    useEventStore.setState({ events: [event("a", "critical", 10), event("b", "low", 12), event("far", "critical", 120)] });
    useMapStore.setState({ viewport: { bbox: [0, -10, 20, 10], zoom: 3, center: { lat: 0, lng: 10 } } });
  });

  it("sums up the view in one line that opens the list", () => {
    render(<MobileViewBar />);
    const bar = screen.getByRole("button", { name: /2 in view/ });
    expect(bar).toHaveTextContent("Critical 1");
    fireEvent.click(bar);
    expect(useUiStore.getState().rightPanel).toBe("in-view");
  });

  it("opens the timeline or the legend from the View menu, one at a time", () => {
    render(<MapControls is3D onToggleProjection={() => {}} />);
    fireEvent.click(screen.getByRole("button", { name: "View" }));
    fireEvent.click(screen.getByRole("menuitemcheckbox", { name: "Timeline" }));
    expect(useUiStore.getState().phoneOverlay).toBe("timeline");

    fireEvent.click(screen.getByRole("button", { name: "View" }));
    fireEvent.click(screen.getByRole("menuitemcheckbox", { name: "Legend" }));
    expect(useUiStore.getState().phoneOverlay).toBe("legend");
  });

  it("keeps the legend hidden on phones until it is asked for", () => {
    const { container } = render(<MapLegend events={[event("a", "critical", 10)]} />);
    const legend = container.firstElementChild!;
    expect(legend).toHaveClass("hidden", "lg:block");
    act(() => useUiStore.setState({ phoneOverlay: "legend" }));
    expect(container.firstElementChild).toHaveClass("block");
    expect(container.firstElementChild).not.toHaveClass("hidden");
  });
});
