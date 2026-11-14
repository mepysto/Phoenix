import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import type { ApiDisasterEvent } from "@/lib/api/client";
import { MapLegend } from "@/components/map/MapLegend";
import { useSettingsStore } from "@/store/settingsStore";

const event = (id: string, type: string, isActive: boolean) =>
  ({ id, type, severity: "medium", isActive }) as unknown as ApiDisasterEvent;

describe("MapLegend", () => {
  beforeEach(() => useSettingsStore.getState().setLanguage("en"));

  it("counts active events only, the same figure as the intro and dashboard", () => {
    render(
      <MapLegend
        events={[event("a", "flood", true), event("b", "flood", true), event("c", "earthquake", false)]}
      />,
    );

    expect(screen.getByText(/Active Events/)).toHaveTextContent("Active Events: 2");
    // Ended events still on the map are named separately, not folded in
    expect(screen.getByText("3 on the map, including ended")).toBeInTheDocument();
  });

  it("explains colour as severity and lists only the types on the map", () => {
    render(<MapLegend events={[event("a", "flood", true)]} />);

    expect(screen.getByText("Colour = severity")).toBeInTheDocument();
    for (const level of ["Low", "Medium", "High", "Critical"]) {
      expect(screen.getByText(level)).toBeInTheDocument();
    }
    expect(screen.getByText("Icon = type")).toBeInTheDocument();
    expect(screen.getByText("Flood")).toBeInTheDocument();
    expect(screen.queryByText("Earthquake")).not.toBeInTheDocument();
    expect(screen.queryByText(/on the map, including ended/)).not.toBeInTheDocument();
  });
});
