/**
 * Recovery site planning against the Sphere minimum standards
 * (The Sphere Handbook, 2018 edition) and common UNHCR planning figures.
 *
 * These are *minimums for a first check*, not a design: a real site plan
 * needs local engineers, the affected community and the authorities.
 *
 * Figures used:
 * - Covered living space: 3.5 m² per person (Shelter and settlement std 3).
 * - Site area: 45 m² per person in camp-type settlements, including
 *   household plots and shared services (Shelter and settlement std 2).
 * - Water quantity: at least 15 litres per person per day (WASH water
 *   supply std 2.1). At most 250 people per tap (WASH 2.1, guidance).
 * - Distance to water point: at most 500 m from any household (WASH 2.1).
 * - Toilets: at most 20 people per toilet (WASH excreta management std 3.2;
 *   50 is accepted in the first days); at most 50 m from dwellings.
 * - Health: one basic health unit per 10,000 people (UNHCR/WHO planning).
 * - Family tent: 16 m² covered area (UNHCR family tent).
 */

export type ItemKind = "tent" | "tap" | "toilet" | "health" | "distribution";

export interface PlanItem {
  id: string;
  kind: ItemKind;
  lat: number;
  lng: number;
}

export interface Plan {
  population: number;
  items: PlanItem[];
}

export const SPHERE = {
  coveredM2PerPerson: 3.5,
  siteM2PerPerson: 45,
  waterLitresPerPersonDay: 15,
  peoplePerTap: 250,
  waterMaxDistanceM: 500,
  peoplePerToilet: 20,
  peoplePerToiletEmergency: 50,
  toiletMaxDistanceM: 50,
  peoplePerHealthUnit: 10_000,
  tentCoveredM2: 16,
} as const;

/** People a family tent shelters at the Sphere covered-space minimum */
export const PEOPLE_PER_TENT = Math.floor(
  SPHERE.tentCoveredM2 / SPHERE.coveredM2PerPerson,
);

export type Status = "ok" | "warn" | "fail";

export interface Kpi {
  id:
    | "shelter"
    | "space"
    | "water"
    | "toilets"
    | "waterDistance"
    | "toiletDistance"
    | "health"
    | "siteArea";
  /** Measured value and the Sphere target, in the KPI's unit */
  value: number;
  target: number;
  /** 0..1 progress toward the target (capped) */
  progress: number;
  status: Status;
}

const EARTH_M = 6_371_000;

export function distanceM(
  a: { lat: number; lng: number },
  b: { lat: number; lng: number },
): number {
  const p1 = (a.lat * Math.PI) / 180;
  const p2 = (b.lat * Math.PI) / 180;
  const dp = p2 - p1;
  const dl = ((b.lng - a.lng) * Math.PI) / 180;
  const h =
    Math.sin(dp / 2) ** 2 + Math.cos(p1) * Math.cos(p2) * Math.sin(dl / 2) ** 2;
  return 2 * EARTH_M * Math.asin(Math.sqrt(Math.min(1, h)));
}

/** Local metres around a reference point (fine at camp scale) */
function toXY(
  p: { lat: number; lng: number },
  ref: { lat: number; lng: number },
): [number, number] {
  const x =
    (((p.lng - ref.lng) * Math.PI) / 180) *
    EARTH_M *
    Math.cos((ref.lat * Math.PI) / 180);
  const y = (((p.lat - ref.lat) * Math.PI) / 180) * EARTH_M;
  return [x, y];
}

/** Area of the convex hull of the points, in m² (0 for fewer than 3) */
export function hullAreaM2(points: { lat: number; lng: number }[]): number {
  if (points.length < 3) return 0;
  const ref = points[0]!;
  const pts = points
    .map((p) => toXY(p, ref))
    .sort((a, b) => a[0] - b[0] || a[1] - b[1]);
  const cross = (o: number[], a: number[], b: number[]) =>
    (a[0]! - o[0]!) * (b[1]! - o[1]!) - (a[1]! - o[1]!) * (b[0]! - o[0]!);
  const lower: [number, number][] = [];
  for (const p of pts) {
    while (
      lower.length >= 2 &&
      cross(lower[lower.length - 2]!, lower[lower.length - 1]!, p) <= 0
    )
      lower.pop();
    lower.push(p);
  }
  const upper: [number, number][] = [];
  for (const p of [...pts].reverse()) {
    while (
      upper.length >= 2 &&
      cross(upper[upper.length - 2]!, upper[upper.length - 1]!, p) <= 0
    )
      upper.pop();
    upper.push(p);
  }
  const hull = [...lower.slice(0, -1), ...upper.slice(0, -1)];
  let area = 0;
  for (let i = 0; i < hull.length; i++) {
    const [x1, y1] = hull[i]!;
    const [x2, y2] = hull[(i + 1) % hull.length]!;
    area += x1 * y2 - x2 * y1;
  }
  return Math.abs(area) / 2;
}

const ratioStatus = (progress: number): Status =>
  progress >= 1 ? "ok" : progress >= 0.75 ? "warn" : "fail";

/** Share of tents with a facility of `kind` within `maxM` */
function withinShare(items: PlanItem[], kind: ItemKind, maxM: number): number {
  const tents = items.filter((i) => i.kind === "tent");
  const targets = items.filter((i) => i.kind === kind);
  if (tents.length === 0) return 0;
  if (targets.length === 0) return 0;
  const near = tents.filter((t) =>
    targets.some((f) => distanceM(t, f) <= maxM),
  ).length;
  return near / tents.length;
}

export function evaluate(plan: Plan): Kpi[] {
  const pop = Math.max(0, Math.floor(plan.population));
  const count = (k: ItemKind) => plan.items.filter((i) => i.kind === k).length;
  const tents = count("tent");
  const taps = count("tap");
  const toilets = count("toilet");
  const health = count("health");
  const safe = (n: number) => (pop === 0 ? 1 : Math.min(1, n));

  const sheltered = tents * PEOPLE_PER_TENT;
  const covered = pop > 0 ? (tents * SPHERE.tentCoveredM2) / pop : 0;
  const tapCapacity = taps * SPHERE.peoplePerTap;
  const peoplePerToilet = toilets > 0 ? pop / toilets : Infinity;
  const healthNeeded = Math.max(1, Math.ceil(pop / SPHERE.peoplePerHealthUnit));
  const area = hullAreaM2(plan.items);
  const areaPerPerson = pop > 0 ? area / pop : 0;

  const toiletProgress =
    toilets === 0 ? 0 : safe(SPHERE.peoplePerToilet / peoplePerToilet);
  const waterDist = withinShare(plan.items, "tap", SPHERE.waterMaxDistanceM);
  const toiletDist = withinShare(
    plan.items,
    "toilet",
    SPHERE.toiletMaxDistanceM,
  );

  return [
    {
      id: "shelter",
      value: sheltered,
      target: pop,
      progress: safe(sheltered / pop),
      status: ratioStatus(safe(sheltered / pop)),
    },
    {
      id: "space",
      value: round1(covered),
      target: SPHERE.coveredM2PerPerson,
      progress: safe(covered / SPHERE.coveredM2PerPerson),
      status: ratioStatus(safe(covered / SPHERE.coveredM2PerPerson)),
    },
    {
      id: "water",
      value: tapCapacity,
      target: pop,
      progress: safe(tapCapacity / pop),
      status: ratioStatus(safe(tapCapacity / pop)),
    },
    {
      id: "toilets",
      value: Number.isFinite(peoplePerToilet) ? Math.round(peoplePerToilet) : 0,
      target: SPHERE.peoplePerToilet,
      progress: toiletProgress,
      // Up to 50 per toilet is acceptable in the first days
      status:
        toilets === 0
          ? "fail"
          : peoplePerToilet <= SPHERE.peoplePerToilet
            ? "ok"
            : peoplePerToilet <= SPHERE.peoplePerToiletEmergency
              ? "warn"
              : "fail",
    },
    {
      id: "waterDistance",
      value: Math.round(waterDist * 100),
      target: 100,
      progress: waterDist,
      status: ratioStatus(waterDist),
    },
    {
      id: "toiletDistance",
      value: Math.round(toiletDist * 100),
      target: 100,
      progress: toiletDist,
      status: ratioStatus(toiletDist),
    },
    {
      id: "health",
      value: health,
      target: healthNeeded,
      progress: Math.min(1, health / healthNeeded),
      status: ratioStatus(Math.min(1, health / healthNeeded)),
    },
    {
      id: "siteArea",
      value: Math.round(areaPerPerson),
      target: SPHERE.siteM2PerPerson,
      progress: safe(areaPerPerson / SPHERE.siteM2PerPerson),
      status: ratioStatus(safe(areaPerPerson / SPHERE.siteM2PerPerson)),
    },
  ];
}

function round1(n: number): number {
  return Math.round(n * 10) / 10;
}

/** Daily water the population needs at the Sphere minimum, in litres */
export function waterLitresPerDay(population: number): number {
  return Math.max(0, Math.floor(population)) * SPHERE.waterLitresPerPersonDay;
}

let seq = 0;
export function newId(): string {
  seq += 1;
  return `${Date.now().toString(36)}${seq.toString(36)}`;
}

/**
 * A starting layout that meets the minimums: blocks of tents on a grid
 * sized for 45 m² per person, taps and toilets inside each block, health
 * units at the centre. Meant to be edited, not used as is.
 */
export function autoLayout(
  center: { lat: number; lng: number },
  population: number,
): PlanItem[] {
  const pop = Math.max(1, Math.floor(population));
  const tents = Math.ceil(pop / PEOPLE_PER_TENT);
  // Plot per tent so the site gives each person 45 m²
  const cols = Math.ceil(Math.sqrt(tents));
  const rows = Math.ceil(tents / cols);
  // Site area is measured on the outline through the tents, which spans
  // (cols - 1) x (rows - 1) plots: size plots so that outline gives 45 m² each
  const basePlot = Math.sqrt(SPHERE.siteM2PerPerson * PEOPLE_PER_TENT);
  const plotM =
    cols > 1 && rows > 1
      ? Math.max(
          basePlot,
          Math.sqrt((SPHERE.siteM2PerPerson * pop) / ((cols - 1) * (rows - 1))),
        )
      : basePlot;
  const mPerDegLat = (Math.PI / 180) * EARTH_M;
  const mPerDegLng = mPerDegLat * Math.cos((center.lat * Math.PI) / 180);
  const at = (xM: number, yM: number) => ({
    lat: center.lat + yM / mPerDegLat,
    lng: center.lng + xM / mPerDegLng,
  });
  const items: PlanItem[] = [];
  const x0 = (-(cols - 1) * plotM) / 2;
  const y0 = (-(rows - 1) * plotM) / 2;
  let placed = 0;
  for (let r = 0; r < rows && placed < tents; r++) {
    for (let c = 0; c < cols && placed < tents; c++, placed++) {
      items.push({
        id: newId(),
        kind: "tent",
        ...at(x0 + c * plotM, y0 + r * plotM),
      });
    }
  }
  // Toilets: one per 20 people, spread over the tents so each is close by
  const toiletCount = Math.ceil(pop / SPHERE.peoplePerToilet);
  const tentItems = items.filter((i) => i.kind === "tent");
  for (let i = 0; i < toiletCount; i++) {
    const t = tentItems[Math.floor((i * tentItems.length) / toiletCount)]!;
    items.push({
      id: newId(),
      kind: "toilet",
      lat: t.lat + (plotM * 0.35) / mPerDegLat,
      lng: t.lng + (plotM * 0.35) / mPerDegLng,
    });
  }
  // Taps: one per 250 people, at least one per ~400 m cell so all are within 500 m
  const span = Math.max(cols, rows) * plotM;
  const cells = Math.max(1, Math.ceil(span / 400));
  const tapCount = Math.max(
    Math.ceil(pop / SPHERE.peoplePerTap),
    cells * cells,
  );
  const tapCols = Math.ceil(Math.sqrt(tapCount));
  const tapRows = Math.ceil(tapCount / tapCols);
  const w = cols * plotM;
  const h = rows * plotM;
  for (let i = 0; i < tapCount; i++) {
    const c = i % tapCols;
    const r = Math.floor(i / tapCols);
    items.push({
      id: newId(),
      kind: "tap",
      ...at(
        -w / 2 + ((c + 0.5) * w) / tapCols,
        -h / 2 + ((r + 0.5) * h) / tapRows,
      ),
    });
  }
  const healthCount = Math.ceil(pop / SPHERE.peoplePerHealthUnit);
  for (let i = 0; i < healthCount; i++)
    items.push({ id: newId(), kind: "health", ...at(i * 30, 0) });
  items.push({ id: newId(), kind: "distribution", ...at(0, -h / 2 - plotM) });
  return items;
}

/** Compact, URL-safe encoding for sharing a plan */
export function encodePlan(plan: Plan): string {
  const kinds: ItemKind[] = ["tent", "tap", "toilet", "health", "distribution"];
  const rows = plan.items.map((i) => [
    kinds.indexOf(i.kind),
    +i.lat.toFixed(6),
    +i.lng.toFixed(6),
  ]);
  const json = JSON.stringify({ p: plan.population, i: rows });
  const b64 =
    typeof btoa === "function"
      ? btoa(unescape(encodeURIComponent(json)))
      : Buffer.from(json).toString("base64");
  return b64.replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

export function decodePlan(s: string): Plan | null {
  try {
    const b64 = s.replace(/-/g, "+").replace(/_/g, "/");
    const json =
      typeof atob === "function"
        ? decodeURIComponent(escape(atob(b64)))
        : Buffer.from(b64, "base64").toString();
    const data = JSON.parse(json) as {
      p: number;
      i: [number, number, number][];
    };
    const kinds: ItemKind[] = [
      "tent",
      "tap",
      "toilet",
      "health",
      "distribution",
    ];
    if (typeof data.p !== "number" || !Array.isArray(data.i)) return null;
    return {
      population: Math.max(0, Math.min(1_000_000, Math.floor(data.p))),
      items: data.i
        .slice(0, 20_000)
        .filter(
          ([k, lat, lng]) =>
            kinds[k] && Math.abs(lat) <= 90 && Math.abs(lng) <= 180,
        )
        .map(([k, lat, lng]) => ({ id: newId(), kind: kinds[k]!, lat, lng })),
    };
  } catch {
    return null;
  }
}

const KIND_ORDER: ItemKind[] = ["tent", "tap", "toilet", "health", "distribution"];

/** Items in the API's compact form: [kindIndex, lat, lng] */
export function toWire(items: PlanItem[]): [number, number, number][] {
  return items.map((i) => [KIND_ORDER.indexOf(i.kind), +i.lat.toFixed(6), +i.lng.toFixed(6)]);
}

export function fromWire(rows: [number, number, number][]): PlanItem[] {
  return rows.flatMap(([k, lat, lng]) => {
    const kind = KIND_ORDER[k];
    return kind ? [{ id: newId(), kind, lat, lng }] : [];
  });
}
