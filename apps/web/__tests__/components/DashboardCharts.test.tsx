import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ChartCard, RankedBars, SegmentedBar } from "@/components/dashboard/Charts";

describe("dashboard charts", () => {
  it("prints a share inside a segment only when it fits", () => {
    render(
      <SegmentedBar
        total={20}
        data={[
          { key: "low", label: "Low", value: 1, color: "red" },
          { key: "high", label: "High", value: 19, color: "blue" },
        ]}
      />,
    );
    expect(screen.getByText("95%")).toBeInTheDocument();
    expect(screen.queryByText("5%")).not.toBeInTheDocument();
    // ...but every part stays reachable by name and value
    expect(screen.getByLabelText("Low: 1 · 5%")).toBeInTheDocument();
    // Legend names the parts without repeating numbers
    expect(screen.getByText("Low")).toBeInTheDocument();
  });

  it("shows a value at each bar tip and exposes it to keyboard users", () => {
    render(
      <RankedBars
        data={[{ key: "flood", label: "Flood", value: 3 }]}
        format={(v) => `${v} events`}
      />,
    );
    const bar = screen.getByLabelText("Flood: 3 events");
    expect(bar).toHaveAttribute("tabindex", "0");
    fireEvent.focus(bar);
    expect(screen.getAllByText("3 events")).toHaveLength(2); // tip label + tooltip
  });

  it("offers every chart as a table", () => {
    render(
      <ChartCard title="By type" table={{ head: ["Type", "Count"], rows: [["Flood", 3]] }}>
        <div />
      </ChartCard>,
    );
    fireEvent.click(screen.getByRole("button", { name: "Show as table" }));
    expect(screen.getByRole("cell", { name: "Flood" })).toBeInTheDocument();
  });
});
