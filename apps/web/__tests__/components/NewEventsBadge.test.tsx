import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { NewEventsBadge } from "@/components/map/NewEventsBadge";
import { useEventStore } from "@/store/eventStore";

const ev = (id: string) => ({ id, type: "flood", severity: "low", title: id }) as never;

describe("NewEventsBadge", () => {
  beforeEach(() => useEventStore.setState({ events: [], newEvents: {} }));

  it("renders nothing without new events", () => {
    render(<NewEventsBadge onSelect={vi.fn()} />);
    expect(screen.queryByRole("button")).toBeNull();
  });

  it("counts only marked events still on the map and opens the newest", () => {
    useEventStore.setState({
      events: [ev("a"), ev("b"), ev("c")],
      newEvents: { a: 1000, b: 3000, gone: 5000 },
    });
    const onSelect = vi.fn();
    render(<NewEventsBadge onSelect={onSelect} />);

    const open = screen.getByRole("button", { name: /2/ });
    fireEvent.click(open);
    expect(onSelect).toHaveBeenCalledWith(expect.objectContaining({ id: "b" }));
  });

  it("dismisses every mark", () => {
    useEventStore.setState({ events: [ev("a")], newEvents: { a: 1000 } });
    render(<NewEventsBadge onSelect={vi.fn()} />);
    fireEvent.click(screen.getAllByRole("button")[1]!);
    expect(useEventStore.getState().newEvents).toEqual({});
    expect(screen.queryByRole("button")).toBeNull();
  });
});
