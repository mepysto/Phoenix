import { afterEach, describe, expect, it, vi } from "vitest";
import { defaultApiUrl } from "@/lib/api/client";

describe("defaultApiUrl", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("targets the API port on the host the page was loaded from", () => {
    // jsdom serves the page from http://localhost:3000
    expect(defaultApiUrl()).toBe(`http://${window.location.hostname}:23180`);
  });

  it("keeps a LAN or Tailscale visitor on the server's address, not their own localhost", () => {
    vi.stubGlobal("window", { location: { protocol: "http:", hostname: "100.103.195.109" } });

    expect(defaultApiUrl()).toBe("http://100.103.195.109:23180");
  });

  it("follows the page protocol so an HTTPS page does not call plain HTTP", () => {
    vi.stubGlobal("window", { location: { protocol: "https:", hostname: "phoenix.example.org" } });

    expect(defaultApiUrl()).toBe("https://phoenix.example.org:23180");
  });

  it("falls back to localhost during server rendering", () => {
    vi.stubGlobal("window", undefined);

    expect(defaultApiUrl()).toBe("http://localhost:23180");
  });
});
