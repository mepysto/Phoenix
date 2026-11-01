import { describe, expect, it } from "vitest";
import {
  PEOPLE_PER_TENT,
  autoLayout,
  decodePlan,
  distanceM,
  encodePlan,
  evaluate,
  hullAreaM2,
  waterLitresPerDay,
  type PlanItem,
} from "@/lib/sphere";

const C = { lat: 24.9, lng: 91.9 };
const kpi = (items: PlanItem[], population: number, id: string) =>
  evaluate({ population, items }).find((k) => k.id === id)!;
const item = (kind: PlanItem["kind"], dxM = 0, dyM = 0): PlanItem => ({
  id: Math.random().toString(36),
  kind,
  lat: C.lat + dyM / 111_195,
  lng: C.lng + dxM / (111_195 * Math.cos((C.lat * Math.PI) / 180)),
});

describe("Sphere figures", () => {
  it("a 16 m² family tent shelters 4 people at 3.5 m² each", () => {
    expect(PEOPLE_PER_TENT).toBe(4);
  });
  it("15 litres per person per day", () => {
    expect(waterLitresPerDay(1000)).toBe(15_000);
  });
});

describe("evaluate", () => {
  it("counts shelter and covered space", () => {
    const tents = Array.from({ length: 25 }, () => item("tent"));
    expect(kpi(tents, 100, "shelter")).toMatchObject({
      value: 100,
      status: "ok",
    });
    expect(kpi(tents, 100, "space").value).toBe(4);
    expect(kpi(tents.slice(0, 20), 100, "shelter").status).toBe("warn");
    expect(kpi(tents.slice(0, 10), 100, "shelter").status).toBe("fail");
  });

  it("toilets: 20 per toilet is ok, up to 50 is acceptable early, more fails", () => {
    const t = (n: number) => Array.from({ length: n }, () => item("toilet"));
    expect(kpi(t(5), 100, "toilets").status).toBe("ok");
    expect(kpi(t(2), 100, "toilets").status).toBe("warn");
    expect(kpi(t(1), 100, "toilets").status).toBe("fail");
    expect(kpi([], 100, "toilets").status).toBe("fail");
  });

  it("water capacity is 250 people per tap", () => {
    expect(kpi([item("tap")], 250, "water").status).toBe("ok");
    expect(kpi([item("tap")], 400, "water").status).toBe("fail");
  });

  it("measures how many tents have water within 500 m and a toilet within 50 m", () => {
    const items = [
      item("tent", 0),
      item("tent", 800),
      item("tap", 100),
      item("toilet", 30),
    ];
    expect(kpi(items, 8, "waterDistance").value).toBe(50);
    expect(kpi(items, 8, "toiletDistance").value).toBe(50);
  });

  it("asks for one health unit per 10,000 people", () => {
    expect(kpi([item("health")], 9_000, "health").status).toBe("ok");
    expect(kpi([item("health")], 15_000, "health")).toMatchObject({
      target: 2,
      status: "fail",
    });
  });
});

describe("geometry", () => {
  it("distance", () => {
    expect(
      Math.round(distanceM({ lat: 0, lng: 0 }, { lat: 0, lng: 1 }) / 1000),
    ).toBe(111);
  });
  it("hull area of a 100 m square is 10,000 m²", () => {
    const sq = [
      item("tent", 0, 0),
      item("tent", 100, 0),
      item("tent", 100, 100),
      item("tent", 0, 100),
      item("tent", 50, 50),
    ];
    expect(hullAreaM2(sq)).toBeGreaterThan(9_900);
    expect(hullAreaM2(sq)).toBeLessThan(10_100);
  });
});

describe("autoLayout", () => {
  it("meets every minimum for the population it was made for", () => {
    for (const pop of [200, 1_000, 5_000]) {
      const kpis = evaluate({ population: pop, items: autoLayout(C, pop) });
      for (const k of kpis)
        expect([pop, k.id, k.status]).toEqual([pop, k.id, "ok"]);
    }
  });
});

describe("share links", () => {
  it("round-trips", () => {
    const items = autoLayout(C, 100);
    const plan = decodePlan(encodePlan({ population: 100, items }))!;
    expect(plan.population).toBe(100);
    expect(plan.items.map((i) => i.kind)).toEqual(items.map((i) => i.kind));
    expect(plan.items[0]!.lat).toBeCloseTo(items[0]!.lat, 5);
  });
  it("rejects garbage", () => {
    expect(decodePlan("not-base64!!")).toBeNull();
  });
});
