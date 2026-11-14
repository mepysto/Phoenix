import { describe, expect, it } from "vitest";
import {
  parseEventQuery,
  periodStart,
  serializeEventQuery,
  sharedFilterQuery,
  toEventFilter,
} from "@/lib/eventQuery";

const NOW = Date.parse("2026-11-14T12:00:00Z");

describe("event filters in the URL, shared by the map and the list", () => {
  it("reads the same keys the map writes (t, s) plus search, period and sort", () => {
    const q = parseEventQuery(new URLSearchParams("t=flood,storm&s=high,critical&q=valencia&period=7&sort=recent"));
    expect(q).toEqual({
      types: ["flood", "storm"],
      severities: ["high", "critical"],
      q: "valencia",
      period: "7",
      sort: "recent",
    });
  });

  it("defaults to the most important first and drops what it cannot use", () => {
    expect(parseEventQuery(new URLSearchParams("t=unknown&period=9&sort=loudest&q=%20%20"))).toEqual({
      sort: "importance",
    });
  });

  it("writes only non-default values and keeps unrelated parameters", () => {
    const qs = serializeEventQuery(
      { types: ["flood"], severities: undefined, q: "chad", period: "30", sort: "importance" },
      new URLSearchParams("v=10,20,3"),
    );
    expect(new URLSearchParams(qs).toString()).toBe(new URLSearchParams("v=10,20,3&t=flood&q=chad&period=30").toString());
    expect(serializeEventQuery({ sort: "importance" })).toBe("");
  });

  it("turns a period into a start date", () => {
    expect(periodStart("1", NOW)).toBe("2026-11-13T12:00:00.000Z");
    expect(periodStart(undefined, NOW)).toBeUndefined();
    expect(toEventFilter({ severities: ["high"], period: "7", sort: "importance" }, NOW)).toEqual({
      severities: ["high"],
      startDate: "2026-11-07T12:00:00.000Z",
    });
  });

  it("carries only the filters when moving between the map and the list", () => {
    expect(sharedFilterQuery("?v=1,2,3&t=flood&s=high&event=abc&q=x&period=7&sort=recent&b=satellite")).toBe(
      "t=flood&s=high&q=x&period=7",
    );
    expect(sharedFilterQuery("")).toBe("");
  });
});
