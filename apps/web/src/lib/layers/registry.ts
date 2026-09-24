/**
 * Map overlay layer registry (G-1).
 *
 * Every overlay declares where its data comes from, its licence, whether it
 * needs an API key (GEV model: keyless layers always work, keys only unlock
 * more), and how to resolve its current tiles. The map, the layer panel and
 * the data-source attribution are all driven from this list.
 */

import { COMMERCIAL_DEPLOYMENT } from "@/lib/map/basemaps";
import { HAZARDS_LAYERS } from "./definitions/hazards";
import { INFRASTRUCTURE_LAYERS } from "./definitions/infrastructure";
import { MONITORING_LAYERS } from "./definitions/monitoring";
import { WEATHER_LAYERS } from "./definitions/weather";
import type { LayerDefinition } from "./types";

export type * from "./types";

/** Order matters: it is the layer panel order and the drawing order (later = on top) */
const ALL_LAYER_DEFINITIONS: LayerDefinition[] = [
  ...WEATHER_LAYERS,
  ...HAZARDS_LAYERS,
  ...INFRASTRUCTURE_LAYERS,
  ...MONITORING_LAYERS,
];

/** Layers this deployment may show (commercial deployments drop NC-only sources) */
export const LAYER_DEFINITIONS: LayerDefinition[] = availableLayers(
  ALL_LAYER_DEFINITIONS,
  COMMERCIAL_DEPLOYMENT,
);

export function availableLayers(
  definitions: LayerDefinition[],
  commercial: boolean,
): LayerDefinition[] {
  return commercial ? definitions.filter((d) => d.source.commercialUse) : definitions;
}

/** Every registered layer regardless of deployment (for docs/tests) */
export { ALL_LAYER_DEFINITIONS };

export const LAYER_DEFINITIONS_BY_ID = new Map(LAYER_DEFINITIONS.map((d) => [d.id, d]));
