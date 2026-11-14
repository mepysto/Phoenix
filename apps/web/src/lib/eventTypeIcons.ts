import {
  Activity,
  Biohazard,
  CloudLightning,
  Droplets,
  Factory,
  Flame,
  FlaskConical,
  Mountain,
  MountainSnow,
  Siren,
  Snowflake,
  Sun,
  Swords,
  ThermometerSun,
  Tornado,
  TriangleAlert,
  Waves,
  type LucideIcon,
} from "lucide-react";
import type { EventType } from "@phoenix/shared/types";

/**
 * One icon per event type, used everywhere a type is shown: map markers,
 * the legend, filters and event pages. Colour belongs to severity, so the
 * icon is what tells types apart.
 */
export const EVENT_TYPE_ICONS: Record<EventType, LucideIcon> = {
  earthquake: Activity,
  flood: Droplets,
  wildfire: Flame,
  hurricane: Tornado,
  tsunami: Waves,
  volcano: MountainSnow,
  war: Swords,
  pollution: FlaskConical,
  drought: Sun,
  other: TriangleAlert,
  landslide: Mountain,
  industrial: Factory,
  epidemic: Biohazard,
  storm: CloudLightning,
  coldwave: Snowflake,
  heatwave: ThermometerSun,
  complex_emergency: Siren,
};

export function eventTypeIcon(type: string): LucideIcon {
  return EVENT_TYPE_ICONS[type as EventType] ?? TriangleAlert;
}
