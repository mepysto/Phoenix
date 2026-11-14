import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api/client", () => ({
  agentAPI: { status: vi.fn(), chat: vi.fn() },
  APIError: class extends Error {},
}));

import { AgentPanel } from "@/components/agent/AgentPanel";
import { agentAPI } from "@/lib/api/client";
import { useSettingsStore } from "@/store/settingsStore";

describe("AgentPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useSettingsStore.getState().setLanguage("en");
  });

  it("offers nothing when the server has no assistant", async () => {
    vi.mocked(agentAPI.status).mockResolvedValue({ enabled: false } as never);
    const { container } = render(<AgentPanel onSelectEvent={vi.fn()} />);

    await waitFor(() => expect(agentAPI.status).toHaveBeenCalled());
    expect(container).toBeEmptyDOMElement();
  });

  it("offers nothing when the status check fails", async () => {
    vi.mocked(agentAPI.status).mockRejectedValue(new Error("offline"));
    const { container } = render(<AgentPanel onSelectEvent={vi.fn()} />);

    await waitFor(() => expect(agentAPI.status).toHaveBeenCalled());
    expect(container).toBeEmptyDOMElement();
  });

  it("shows the button once the assistant is available", async () => {
    vi.mocked(agentAPI.status).mockResolvedValue({ enabled: true } as never);
    render(<AgentPanel onSelectEvent={vi.fn()} />);

    expect(await screen.findByRole("button", { name: "Ask the map" })).toBeInTheDocument();
  });
});
