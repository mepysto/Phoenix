import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api/client", () => ({ sourcesAPI: { list: vi.fn() } }));

import { sourcesAPI } from "@/lib/api/client";
import { formatAge, SourceStatusPanel } from "@/components/layout/SourceStatusPanel";
import { useSettingsStore } from "@/store/settingsStore";

const source = (over: Record<string, unknown>) => ({
  name: "USGS",
  type: "disaster_alert",
  isRealtime: true,
  status: "fresh",
  lastSync: new Date(Date.now() - 3 * 60_000).toISOString(),
  syncIntervalMinutes: 5,
  consecutiveFailures: 0,
  lastError: null,
  ...over,
});

describe("SourceStatusPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useSettingsStore.getState().setLanguage("en");
  });

  it("shows age for fresh sources and a status for the others", async () => {
    vi.mocked(sourcesAPI.list).mockResolvedValue([
      source({}),
      source({ name: "GDACS", status: "failing", lastError: "ExternalAPIError" }),
      source({ name: "EONET", status: "never", lastSync: null }),
    ] as never);

    render(<SourceStatusPanel />);

    expect(await screen.findByText("Data sources")).toBeInTheDocument();
    expect(screen.getByText("3 min. ago")).toBeInTheDocument();
    expect(screen.getByText("Failing")).toHaveAttribute("title", "ExternalAPIError");
    expect(screen.getByLabelText("EONET: No data yet")).toBeInTheDocument();
  });

  it("renders nothing when the status API is unreachable", async () => {
    vi.mocked(sourcesAPI.list).mockRejectedValue(new Error("offline"));
    const { container } = render(<SourceStatusPanel />);
    await waitFor(() => expect(sourcesAPI.list).toHaveBeenCalled());
    expect(container).toBeEmptyDOMElement();
  });
});

describe("formatAge", () => {
  const now = Date.parse("2026-09-24T12:00:00Z");
  it("uses the UI language", () => {
    expect(formatAge("2026-09-24T11:57:00Z", "en", now)).toBe("3 min. ago");
    expect(formatAge("2026-09-24T09:00:00Z", "ko", now)).toBe("3시간 전");
  });
  it("returns null for sources that never synced", () => {
    expect(formatAge(null, "en", now)).toBeNull();
  });
});
