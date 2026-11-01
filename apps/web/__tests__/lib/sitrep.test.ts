import { describe, expect, it } from "vitest";
import { buildSitrep, sitrepToText } from "@/lib/sitrep";
import { translations } from "@/lib/i18n/translations";

const t = translations.en;

const event = {
  title: "M6.8 earthquake near Coast",
  type: "earthquake" as const,
  severity: "high" as const,
  description: null,
  location: {
    lat: 10,
    lng: 20,
    country: "Testland",
    countryCode: null,
    region: null,
  },
  startDate: "2026-10-30T03:00:00Z",
  endDate: null,
  isActive: true,
  affectedPopulation: 12000,
  sources: [{ id: "1", name: "USGS", type: "api" }],
  trust: {
    confidence: 0.6,
    sourceCount: 1,
    lifecycle: "responding" as const,
    reasons: [],
  },
};

describe("buildSitrep", () => {
  const nearby = [
    {
      event: {
        id: "2",
        title: "Aftershock",
        severity: "medium" as const,
        type: "earthquake" as const,
      },
      distanceKm: 42.4,
    },
  ];
  const report = buildSitrep(
    event,
    nearby,
    t,
    "en",
    new Date("2026-11-01T00:00:00Z"),
  );

  it("states what, where and how sure, from the event's own fields", () => {
    const summary = report.sections.find((s) => s.id === "summary")!;
    expect(summary.lines[0]).toBe("Earthquake of high severity in Testland.");
    const confidence = report.sections.find((s) => s.id === "confidence")!;
    expect(confidence.lines[0]).toContain("60%");
    expect(confidence.lines[0]).toContain("Response");
  });

  it("lists neighbours with distance", () => {
    const near = report.sections.find((s) => s.id === "nearby")!;
    expect(near.lines[0]).toBe("Aftershock, 42 km away (medium)");
  });

  it("asks for a second source when only one reports the event", () => {
    const next = report.sections.find((s) => s.id === "next")!;
    expect(next.lines).toContain(t.sitrep.nextSecondSource);
    expect(next.lines).toContain(t.sitrep.nextCompound);
  });

  it("says so when there is nothing nearby and no population estimate", () => {
    const r = buildSitrep({ ...event, affectedPopulation: null }, [], t, "en");
    expect(r.sections.find((s) => s.id === "nearby")!.lines).toEqual([
      t.sitrep.lineNoNearby,
    ]);
    expect(r.sections.find((s) => s.id === "impact")!.lines).toEqual([
      t.sitrep.lineNoPopulation,
    ]);
  });

  it("renders as plain text with the disclaimer", () => {
    const text = sitrepToText(report, t);
    expect(
      text.startsWith("Situation report: M6.8 earthquake near Coast"),
    ).toBe(true);
    expect(text).toContain("- Aftershock, 42 km away (medium)");
    expect(text.trim().endsWith(t.sitrep.disclaimer)).toBe(true);
  });

  it("every locale fills the same templates", () => {
    for (const [lang, tr] of Object.entries(translations)) {
      const r = buildSitrep(event, nearby, tr, lang);
      for (const s of r.sections)
        for (const l of s.lines) expect(l).not.toMatch(/\{\w+\}/);
    }
  });
});
