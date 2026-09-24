import { describe, expect, it } from "vitest";
import { compassPoint, numberProp, shipCategory, stringProp } from "@/lib/telemetry";

describe("telemetry helpers", () => {
  it("maps AIS ship type codes", () => {
    expect(shipCategory(30)).toBe("fishing");
    expect(shipCategory(51)).toBe("searchRescue");
    expect(shipCategory(58)).toBe("medical");
    expect(shipCategory(64)).toBe("passenger");
    expect(shipCategory(79)).toBe("cargo");
    expect(shipCategory(84)).toBe("tanker");
    expect(shipCategory(99)).toBe("other");
    expect(shipCategory(0)).toBeNull();
    expect(shipCategory(null)).toBeNull();
  });

  it("names compass points", () => {
    expect(compassPoint(0)).toBe("N");
    expect(compassPoint(44)).toBe("NE");
    expect(compassPoint(272.7)).toBe("W");
    expect(compassPoint(359)).toBe("N");
    expect(compassPoint(-90)).toBe("W");
  });

  it("reads feature properties defensively", () => {
    expect(numberProp(3)).toBe(3);
    expect(numberProp("3")).toBeNull();
    expect(numberProp(Number.NaN)).toBeNull();
    expect(stringProp("  JAL1 ")).toBe("JAL1");
    expect(stringProp("")).toBeNull();
    expect(stringProp(null)).toBeNull();
  });
});
