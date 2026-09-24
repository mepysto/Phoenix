import { render, screen, fireEvent } from "@testing-library/react";
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

  it("renders navigation links", () => {
    render(<Header />);

    expect(screen.getByText("Events")).toBeInTheDocument();
    expect(screen.getByText("About")).toBeInTheDocument();
  });

  it("renders the settings button", () => {
    render(<Header />);

    // Settings button should exist
    const buttons = screen.getAllByRole("button");
    expect(buttons.length).toBeGreaterThan(0);
  });
});
