import { render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/components/layout/Header", () => ({ Header: () => null }));
vi.mock("@/lib/api/community", () => ({ statsAPI: { overview: vi.fn() } }));

import DashboardPage from "@/app/dashboard/page";
import { statsAPI, type OverviewStats } from "@/lib/api/community";
import { useSettingsStore } from "@/store/settingsStore";

const stats = (over: Partial<OverviewStats>): OverviewStats => ({
  generatedAt: new Date().toISOString(),
  activeEvents: 223,
  criticalActive: 12,
  affectedActive: 0,
  affectedEstimated: 0,
  countriesActive: 0,
  newThisWeek: 121,
  newWeekBefore: 0,
  byType: [{ type: "earthquake", events: 125, affected: 0 }],
  bySeverity: [
    { severity: "low", events: 10 },
    { severity: "medium", events: 190 },
    { severity: "high", events: 11 },
    { severity: "critical", events: 12 },
  ],
  weeklyOnsets: [{ weekStart: "2026-11-09", events: 96 }],
  topAffected: [],
  needsOpen: 0,
  offersOpen: 0,
  connectionsMade: 0,
  needsByCategory: [],
  ...over,
});

describe("Dashboard without people-affected figures", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useSettingsStore.getState().setLanguage("en");
  });

  it("says 'not yet counted' instead of showing zero people and zero countries", async () => {
    vi.mocked(statsAPI.overview).mockResolvedValue(stats({}));
    render(<DashboardPage />);

    // The headline is a figure we have: active events
    const headline = (await screen.findByText("223")).closest("div")!;
    expect(within(headline).getByText("Active events")).toBeInTheDocument();

    for (const label of ["People affected by active events", "Countries"]) {
      const tile = screen.getByText(label).parentElement!;
      expect(within(tile).getByText("Not yet counted")).toBeInTheDocument();
      expect(within(tile).queryByText("0")).not.toBeInTheDocument();
    }
    expect(screen.getByText("Nothing to show yet.")).toBeInTheDocument(); // most affected
    // A people/events switch over all-zero data would be noise
    expect(screen.queryByRole("button", { name: "People affected" })).not.toBeInTheDocument();
  });

  it("leads with people affected, and how many events it rests on, once estimates exist", async () => {
    vi.mocked(statsAPI.overview).mockResolvedValue(
      stats({ affectedActive: 120_000, affectedEstimated: 4, countriesActive: 3 }),
    );
    render(<DashboardPage />);

    expect(await screen.findByText(/From 4 events with an estimate/)).toBeInTheDocument();
    expect(screen.queryByText("Not yet counted")).not.toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument(); // countries
  });
});
