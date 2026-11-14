import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api/client", async (orig) => ({
  ...(await orig<typeof import("@/lib/api/client")>()),
  eventsAPI: { list: vi.fn().mockResolvedValue({ data: [], pagination: { total: 0 } }), facets: vi.fn() },
}));

import { Sidebar } from "@/components/layout/Sidebar";
import { plainLayerName } from "@/components/layout/sidebar/LayerList";
import { eventsAPI } from "@/lib/api/client";
import { useEventStore } from "@/store/eventStore";
import { useMapStore } from "@/store/mapStore";
import { useSettingsStore } from "@/store/settingsStore";

describe("Map filter panel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useSettingsStore.getState().setLanguage("en");
    useEventStore.getState().setVisibility(undefined, undefined);
    vi.mocked(eventsAPI.facets).mockResolvedValue({
      total: 150,
      byType: { earthquake: 120, flood: 30 },
      bySeverity: { critical: 5, medium: 145 },
    });
  });

  it("shows severity and the types that have events, each with its count", async () => {
    render(<Sidebar />);
    const types = screen.getByRole("region", { name: "Event types" });

    await waitFor(() => expect(within(types).getByText("120")).toBeInTheDocument());
    expect(within(types).getByText("Earthquake")).toBeInTheDocument();
    expect(within(types).queryByText("Tsunami")).not.toBeInTheDocument();
    expect(within(screen.getByRole("region", { name: "Severity" })).getByText("5")).toBeInTheDocument();

    fireEvent.click(within(types).getByRole("button", { name: "15 more types" }));
    expect(within(types).getByText("Tsunami")).toBeInTheDocument();
  });

  it("clears and restores every type at once", async () => {
    render(<Sidebar />);
    fireEvent.click(await screen.findByRole("button", { name: "Clear all" }));
    expect(useEventStore.getState().visibleTypes.size).toBe(0);
    fireEvent.click(screen.getByRole("button", { name: "Select all" }));
    expect(useEventStore.getState().visibleTypes.size).toBeGreaterThan(10);
  });

  it("groups overlays in plain words, with source and zoom on the line below", () => {
    render(<Sidebar />);
    fireEvent.click(screen.getByRole("tab", { name: "Layers" }));

    for (const group of ["Hazards", "Satellite imagery", "Infrastructure", "Live tracking"]) {
      expect(screen.getByRole("region", { name: group })).toBeInTheDocument();
    }
    const aircraft = screen.getByRole("switch", { name: "Aircraft" });
    expect(aircraft).toHaveAttribute("aria-checked", "false");
    expect(screen.getByText("adsb.lol · From zoom 5")).toBeInTheDocument();

    fireEvent.click(aircraft);
    expect(useMapStore.getState().layers.find((l) => l.id === "aircraft")?.visible).toBe(true);
    expect(screen.getByRole("switch", { name: "Aircraft" })).toHaveAttribute("aria-checked", "true");
  });

  it("strips technical detail from layer names", () => {
    expect(plainLayerName("Aircraft (ADS-B, zoom 5+)")).toBe("Aircraft");
    expect(plainLayerName("Night Lights (VIIRS)")).toBe("Night Lights");
    expect(plainLayerName("Hospitals")).toBe("Hospitals");
  });
});
