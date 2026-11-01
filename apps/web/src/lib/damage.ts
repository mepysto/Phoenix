/** EMS damage classes, worst first, with their map colours. No map code here. */
export const DAMAGE_GRADES = [
  "destroyed",
  "damaged",
  "possibly_damaged",
  "no_visible_damage",
  "unknown",
] as const;
export type DamageGrade = (typeof DAMAGE_GRADES)[number];

export const DAMAGE_COLORS: Record<DamageGrade, string> = {
  destroyed: "#e5501f",
  damaged: "#ff8a5b",
  possibly_damaged: "#f5b83d",
  no_visible_damage: "#7889a6",
  unknown: "#44536e",
};

/**
 * Read a per-grade value from an API response. The client camel-cases every
 * key, including the keys of these maps ("possibly_damaged" arrives as
 * "possiblyDamaged"), so look up both spellings.
 */
export function byGrade<T>(
  map: Record<string, T | undefined> | undefined,
  grade: DamageGrade,
): T | undefined {
  if (!map) return undefined;
  const camel = grade.replace(/_([a-z])/g, (_, c: string) => c.toUpperCase());
  return map[camel] ?? map[grade];
}
