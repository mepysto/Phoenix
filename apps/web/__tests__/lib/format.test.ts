import { describe, expect, it } from "vitest";
import { formatDate, formatMoment, formatRelative, formatWhen } from "@/lib/format";

const NOW = Date.parse("2026-11-02T12:00:00Z");

describe("format", () => {
  it("writes relative time in the reader's language", () => {
    expect(formatRelative(NOW - 3 * 3600_000, "en", NOW)).toBe("3 hours ago");
    expect(formatRelative(NOW - 24 * 3600_000, "en", NOW)).toBe("yesterday");
    expect(formatRelative(NOW - 10_000, "en", NOW)).toBe("now");
    expect(formatRelative(NOW - 3 * 3600_000, "ko", NOW)).toBe("3시간 전");
  });

  it("switches to an absolute date after a week", () => {
    expect(formatWhen(NOW - 2 * 86400_000, "en", NOW)).toBe("2 days ago");
    expect(formatWhen("2026-10-01T00:00:00Z", "en", NOW)).toBe(
      formatDate("2026-10-01T00:00:00Z", "en"),
    );
  });

  it("never prints a bare numeric date", () => {
    expect(formatDate("2026-10-20T12:00:00Z", "en")).toMatch(/Oct/);
  });

  it("writes a detail moment as relative time plus the exact UTC time", () => {
    const at = "2026-11-02T09:00:00Z";
    expect(formatMoment(at, "en", NOW)).toBe("3 hours ago · Nov 2, 2026, 09:00 UTC");
    expect(formatMoment(at, "ko", NOW)).toMatch(/^3시간 전 · 2026\. 11\. 2\..*09:00 UTC$/);
  });
});
