import { render, screen, fireEvent, within } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { Header } from "@/components/layout/Header";

const { mockPush } = vi.hoisted(() => ({ mockPush: vi.fn() }));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush, replace: vi.fn(), prefetch: vi.fn() }),
  usePathname: () => "/",
  useSearchParams: () => new URLSearchParams(),
}));

describe("Header", () => {
  it("renders the Phoenix logo and title", () => {
    render(<Header />);

    expect(screen.getByText("Phoenix")).toBeInTheDocument();
  });

  it("renders the search input with correct placeholder", () => {
    render(<Header />);

    const searchInput = screen.getByPlaceholderText(
      "Search events, locations...",
    );
    expect(searchInput).toBeInTheDocument();
  });

  it("updates search input value when user types", () => {
    render(<Header />);

    const searchInput = screen.getByPlaceholderText(
      "Search events, locations...",
    ) as HTMLInputElement;
    fireEvent.change(searchInput, { target: { value: "earthquake" } });

    expect(searchInput.value).toBe("earthquake");
  });

  it("offers four top-level destinations, with the ways to help under Take part", () => {
    render(<Header />);
    const nav = within(screen.getByRole("banner")).getByRole("navigation");

    const links = within(nav).getAllByRole("link").map((a) => [a.textContent, a.getAttribute("href")]);
    expect(links).toEqual([
      ["Map", "/"],
      ["Disasters", "/events"],
      ["Overview", "/dashboard"],
    ]);
    // Secondary pages are not in the main menu any more
    expect(within(nav).queryByText("About")).not.toBeInTheDocument();

    fireEvent.click(within(nav).getByRole("button", { name: /Take part/ }));
    expect(within(nav).getByRole("link", { name: /Needs and offers/ })).toHaveAttribute("href", "/connect");
    expect(within(nav).getByRole("link", { name: /Site planner/ })).toHaveAttribute("href", "/plan");
    expect(within(nav).getByRole("link", { name: /Design challenges/ })).toHaveAttribute("href", "/challenges");
  });

  it("keeps sign-in, language, settings and about in one account menu", () => {
    render(<Header />);
    const banner = screen.getByRole("banner");

    fireEvent.click(within(banner).getByRole("button", { name: "Account" }));

    expect(within(banner).getByRole("link", { name: "Sign in" })).toHaveAttribute("href", "/login");
    expect(within(banner).getByLabelText("Language")).toBeInTheDocument();
    expect(within(banner).getByRole("link", { name: "Settings" })).toHaveAttribute("href", "/settings");
    expect(within(banner).getByRole("link", { name: "About" })).toHaveAttribute("href", "/about");
  });

  it("gives phones a four-tab bar with Take part opening the ways to help", () => {
    render(<Header />);
    const tabs = document.getElementById("bottom-nav")!;

    expect(within(tabs).getAllByRole("link").map((a) => a.textContent)).toEqual(["Map", "Disasters", "Overview"]);
    fireEvent.click(within(tabs).getByRole("button", { name: "Take part" }));
    expect(screen.getByRole("navigation", { name: "Take part" })).toBeInTheDocument();
  });
});
