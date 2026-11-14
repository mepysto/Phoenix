import { act, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const nav = vi.hoisted(() => ({ search: "" }));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), prefetch: vi.fn() }),
  usePathname: () => "/alerts",
  useSearchParams: () => new URLSearchParams(nav.search),
}));
vi.mock("next/dynamic", () => ({ default: () => () => null }));
vi.mock("@/components/layout/Header", () => ({ Header: () => null }));
vi.mock("@/components/plan/PlanSaveBar", () => ({ PlanSaveBar: () => null }));
vi.mock("@/lib/api/client", async (orig) => ({
  ...(await orig<typeof import("@/lib/api/client")>()),
  placesAPI: { search: vi.fn() },
  eventsAPI: { list: vi.fn().mockResolvedValue({ data: [] }), get: vi.fn() },
}));

import AlertsPage from "@/app/alerts/page";
import PlanPage from "@/app/plan/page";
import { PlaceSearch } from "@/components/ui/PlaceSearch";
import { placesAPI, type ApiPlace } from "@/lib/api/client";
import { useSettingsStore } from "@/store/settingsStore";

const place = (over: Partial<ApiPlace>): ApiPlace => ({
  id: 1,
  name: "Seoul",
  admin1: null,
  country: "South Korea",
  countryCode: "KR",
  lat: 37.566,
  lng: 126.978,
  population: 10_000_000,
  ...over,
});

async function typeAndWait(input: HTMLElement, value: string) {
  fireEvent.change(input, { target: { value } });
  await act(async () => {
    await vi.advanceTimersByTimeAsync(250);
  });
}

describe("PlaceSearch", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    useSettingsStore.getState().setLanguage("en");
    vi.mocked(placesAPI.search).mockResolvedValue([
      place({}),
      place({ id: 2, name: "Seongnam-si", admin1: "Gyeonggi-do", lat: 37.43, lng: 127.13 }),
    ]);
  });
  afterEach(() => vi.useRealTimers());

  it("lists places as you type and picks with the keyboard", async () => {
    const onPick = vi.fn();
    render(<PlaceSearch onPick={onPick} />);
    const box = screen.getByRole("combobox", { name: "Search for a place" });

    await typeAndWait(box, "s"); // one letter: no request
    expect(placesAPI.search).not.toHaveBeenCalled();
    await typeAndWait(box, "seo");
    expect(placesAPI.search).toHaveBeenCalledWith("seo", expect.anything());

    const list = screen.getByRole("listbox");
    expect(within(list).getAllByRole("option").map((o) => o.textContent)).toEqual([
      "Seoul, South Korea",
      "Seongnam-si, Gyeonggi-do, South Korea",
    ]);
    expect(screen.getByText("Place names: GeoNames (CC BY 4.0)")).toBeInTheDocument();
    expect(box).toHaveAttribute("aria-activedescendant", expect.stringMatching(/-0$/));

    fireEvent.keyDown(box, { key: "ArrowDown" });
    fireEvent.keyDown(box, { key: "Enter" });
    expect(onPick).toHaveBeenCalledWith(expect.objectContaining({ name: "Seongnam-si" }));
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
  });

  it("says so when nothing matches", async () => {
    vi.mocked(placesAPI.search).mockResolvedValue([]);
    render(<PlaceSearch onPick={vi.fn()} />);
    await typeAndWait(screen.getByRole("combobox"), "zzzz");
    expect(screen.getByText("No town or city by that name")).toBeInTheDocument();
  });

  it("sets an alert area's centre and name from a place", async () => {
    localStorage.clear();
    render(<AlertsPage />);
    await typeAndWait(screen.getByRole("combobox", { name: "Search for a place" }), "seo");
    fireEvent.mouseDown(screen.getByRole("option", { name: "Seoul, South Korea" }));

    expect(screen.getByText("Centre: 37.57, 126.98")).toBeInTheDocument();
    expect(screen.getByLabelText("Name")).toHaveValue("Seoul");
  });

  it("starts a site plan at a place", async () => {
    nav.search = "";
    window.history.replaceState(null, "", "/plan");
    render(<PlanPage />);
    await typeAndWait(screen.getByRole("combobox", { name: "Or start at a town or city" }), "seo");
    fireEvent.mouseDown(screen.getByRole("option", { name: "Seoul, South Korea" }));

    expect(screen.getByText("Seoul, South Korea", { selector: "span" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Which disaster is this site for?" })).not.toBeInTheDocument();
  });
});

describe("Alert notifications", () => {
  beforeEach(() => {
    localStorage.clear();
    useSettingsStore.getState().setLanguage("en");
  });

  afterEach(() => vi.unstubAllGlobals());

  it("puts both ways of being told in one section, each saying what it does", () => {
    vi.stubGlobal("Notification", { permission: "default", requestPermission: vi.fn() });
    render(<AlertsPage />);
    const section = screen.getByRole("region", { name: "How you are told" });
    expect(within(section).getByRole("heading", { name: "While Phoenix is open" })).toBeInTheDocument();
    expect(within(section).getByRole("heading", { name: "Even when Phoenix is closed" })).toBeInTheDocument();
    expect(within(section).getByText(/as long as a Phoenix tab is open/)).toBeInTheDocument();
  });

  it("says plainly when the browser cannot notify", () => {
    render(<AlertsPage />);
    const section = screen.getByRole("region", { name: "How you are told" });
    expect(within(section).getByText("This browser cannot show notifications.")).toBeInTheDocument();
  });
});
