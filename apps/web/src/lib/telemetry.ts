/** Helpers for the telemetry cards of moving objects (G-15) */

export type ShipCategory =
  | "fishing"
  | "towing"
  | "military"
  | "sailing"
  | "pleasure"
  | "highSpeed"
  | "pilot"
  | "searchRescue"
  | "tug"
  | "lawEnforcement"
  | "medical"
  | "passenger"
  | "cargo"
  | "tanker"
  | "other";

/** AIS "type of ship and cargo" code → category (ITU-R M.1371) */
export function shipCategory(code: number | null | undefined): ShipCategory | null {
  if (code == null || !Number.isFinite(code) || code <= 0) return null;
  const exact: Record<number, ShipCategory> = {
    30: "fishing",
    31: "towing",
    32: "towing",
    35: "military",
    36: "sailing",
    37: "pleasure",
    50: "pilot",
    51: "searchRescue",
    52: "tug",
    55: "lawEnforcement",
    58: "medical",
  };
  if (exact[code]) return exact[code];
  if (code >= 40 && code <= 49) return "highSpeed";
  if (code >= 60 && code <= 69) return "passenger";
  if (code >= 70 && code <= 79) return "cargo";
  if (code >= 80 && code <= 89) return "tanker";
  return "other";
}

/** Compass point for a heading in degrees (N, NE, ...) */
export function compassPoint(degrees: number): string {
  const points = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"];
  return points[Math.round((((degrees % 360) + 360) % 360) / 45) % 8]!;
}

export const numberProp = (value: unknown): number | null =>
  typeof value === "number" && Number.isFinite(value) ? value : null;
export const stringProp = (value: unknown): string | null =>
  typeof value === "string" && value.trim() ? value.trim() : null;
