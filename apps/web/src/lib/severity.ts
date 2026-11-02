import type { SeverityLevel } from "@phoenix/shared/types";

export const SEVERITY_LEVELS: SeverityLevel[] = ["low", "medium", "high", "critical"];

/** Theme-aware severity colour for DOM styles (light and dark steps in globals.css) */
export const severityColor = (level: string): string =>
  `var(--sev-${SEVERITY_LEVELS.includes(level as SeverityLevel) ? level : "low"})`;
