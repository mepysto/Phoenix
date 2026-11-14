import { act, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { IntroGlobe } from "@/components/brand/IntroGlobe";
import { useSettingsStore } from "@/store/settingsStore";

const SEEN_KEY = "phoenix:intro-seen";

describe("IntroGlobe", () => {
  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
    window.history.replaceState(null, "", "/");
    useSettingsStore.getState().setLanguage("en");
    // jsdom has no canvas; the intro draws nothing but still opens
    vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(null);
  });
  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it("opens on a first visit and steps aside on its own after a few seconds", () => {
    vi.useFakeTimers();
    render(<IntroGlobe events={[]} />);
    expect(screen.getByRole("dialog")).toBeInTheDocument();

    act(() => vi.advanceTimersByTime(3000 + 700));

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    // Remembered for the device, not just this tab
    expect(localStorage.getItem(SEEN_KEY)).toBe("1");
  });

  it("does not show again on this device", () => {
    localStorage.setItem(SEEN_KEY, "1");
    render(<IntroGlobe events={[]} />);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("is skipped for a shared link that opens a specific view", () => {
    window.history.replaceState(null, "", "/?event=abc");
    render(<IntroGlobe events={[]} />);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});
