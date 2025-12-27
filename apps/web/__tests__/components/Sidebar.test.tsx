import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { Sidebar } from "@/components/layout/Sidebar";

// Mock the eventStore
const mockToggleEventType = vi.fn();
const mockToggleSeverity = vi.fn();

vi.mock("@/store/eventStore", () => ({
  useEventStore: () => ({
    filter: {
      types: [],
      severities: [],
    },
    toggleEventType: mockToggleEventType,
    toggleSeverity: mockToggleSeverity,
    events: [],
    isLoading: false,
  }),
}));

describe("Sidebar", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the sidebar title", () => {
    render(<Sidebar />);

    expect(screen.getByText("Layers & Filters")).toBeInTheDocument();
  });

  it("renders Event Types section", () => {
    render(<Sidebar />);

    expect(screen.getByText("Event Types")).toBeInTheDocument();
  });

  it("renders Severity section", () => {
    render(<Sidebar />);

    expect(screen.getByText("Severity")).toBeInTheDocument();
  });

  it("renders Layers section", () => {
    render(<Sidebar />);

    expect(screen.getByText("Layers")).toBeInTheDocument();
  });

  it("renders event type filter options", () => {
    render(<Sidebar />);

    // Check for some event types from EVENT_TYPE_LABELS
    expect(screen.getByText("Earthquake")).toBeInTheDocument();
    expect(screen.getByText("Flood")).toBeInTheDocument();
    expect(screen.getByText("Wildfire")).toBeInTheDocument();
  });

  it("renders severity filter options", () => {
    render(<Sidebar />);

    // Check for severity levels from SEVERITY_LABELS
    expect(screen.getByText("Low")).toBeInTheDocument();
    expect(screen.getByText("Medium")).toBeInTheDocument();
    expect(screen.getByText("High")).toBeInTheDocument();
    expect(screen.getByText("Critical")).toBeInTheDocument();
  });

  it("renders layer options", () => {
    render(<Sidebar />);

    expect(screen.getByText("Satellite Imagery")).toBeInTheDocument();
    expect(screen.getByText("3D Buildings")).toBeInTheDocument();
    expect(screen.getByText("Population Density")).toBeInTheDocument();
  });

  it("displays event count in footer", () => {
    render(<Sidebar />);

    expect(screen.getByText("0 events")).toBeInTheDocument();
  });

  it("displays data source attribution", () => {
    render(<Sidebar />);

    expect(screen.getByText("Data: GDACS, Copernicus EMS")).toBeInTheDocument();
  });
});
