/**
 * Disaster event markers on the MapLibre map: GeoJSON conversion and the
 * clustered source with its layers and click/hover handlers.
 */
import type { ExpressionSpecification, GeoJSONSource, Map as MapLibreMap } from "maplibre-gl";
import type { ApiDisasterEvent, SeverityLevel } from "@/lib/api/client";
import { getEventPosition } from "@/lib/eventPosition";
import { LABEL_FONT } from "@/lib/map/basemaps";
import { addEventTypeIcons, eventTypeImageId } from "@/lib/map/markerIcons";
import type { MapView } from "@/lib/map/urlState";

type DisasterEvent = ApiDisasterEvent;

/**
 * Marker encoding (docs/UX_REDESIGN_PLAN.md 5.1): colour = severity,
 * icon = event type. A cluster takes the colour of its most severe event.
 */
export const SEVERITY_RANK: Record<SeverityLevel, number> = {
  low: 0,
  medium: 1,
  high: 2,
  critical: 3,
};

const MARKER_RADIUS: Record<SeverityLevel, number> = {
  low: 9,
  medium: 10,
  high: 12,
  critical: 14,
};

export function getMarkerSize(severity: SeverityLevel): number {
  return MARKER_RADIUS[severity] ?? MARKER_RADIUS.medium;
}

export type SeverityColors = Record<SeverityLevel, string>;

// Dark-theme values from globals.css, used when CSS variables are unavailable (tests)
const FALLBACK_SEVERITY_COLORS: SeverityColors = {
  low: "#3987e5",
  medium: "#c98500",
  high: "#e5484d",
  critical: "#9085e9",
};

/** The theme's severity colours (--sev-* in globals.css), as MapLibre needs literal colours */
export function readSeverityColors(): SeverityColors {
  if (typeof document === "undefined") return FALLBACK_SEVERITY_COLORS;
  const style = getComputedStyle(document.documentElement);
  const read = (level: SeverityLevel) =>
    style.getPropertyValue(`--sev-${level}`).trim() || FALLBACK_SEVERITY_COLORS[level];
  return { low: read("low"), medium: read("medium"), high: read("high"), critical: read("critical") };
}

/** Paint expression mapping a severity rank property to the theme colour */
export function severityColorExpression(
  rankProperty: "sevRank" | "maxSev",
  colors: SeverityColors,
): ExpressionSpecification {
  return [
    "match",
    ["get", rankProperty],
    SEVERITY_RANK.critical,
    colors.critical,
    SEVERITY_RANK.high,
    colors.high,
    SEVERITY_RANK.medium,
    colors.medium,
    colors.low,
  ];
}

/** Re-apply severity colours, e.g. after the light/dark theme changes */
export function applySeverityColors(map: MapLibreMap, colors: SeverityColors = readSeverityColors()): void {
  const point = severityColorExpression("sevRank", colors);
  const paints: [string, "circle-color" | "circle-stroke-color", ExpressionSpecification][] = [
    ["clusters", "circle-color", severityColorExpression("maxSev", colors)],
    ["events-layer", "circle-color", point],
    ["events-pulse", "circle-color", point],
    [NEW_EVENTS_LAYER, "circle-stroke-color", point],
  ];
  for (const [layer, property, value] of paints) {
    if (map.getLayer(layer)) map.setPaintProperty(layer, property, value);
  }
}

export function readView(map: MapLibreMap): MapView {
  const center = map.getCenter();
  return {
    lng: center.lng,
    lat: center.lat,
    zoom: map.getZoom(),
    bearing: map.getBearing(),
    pitch: map.getPitch(),
  };
}

/** Map layer that rings events which just arrived from live updates */
export const NEW_EVENTS_LAYER = "events-new";

export function eventsToGeoJSON(
  events: DisasterEvent[],
  newIds: ReadonlySet<string> = new Set(),
): GeoJSON.FeatureCollection {
  const features: GeoJSON.Feature[] = [];
  for (const event of events) {
    const position = getEventPosition(event);
    if (!position) continue; // cannot be placed on the map
    features.push({
      type: "Feature",
      geometry: {
        type: "Point",
        coordinates: [position.lng, position.lat],
      },
      properties: {
        id: event.id,
        title: event.title,
        description: event.description || "",
        type: event.type,
        icon: eventTypeImageId(event.type),
        severity: event.severity,
        sevRank: SEVERITY_RANK[event.severity as SeverityLevel] ?? SEVERITY_RANK.low,
        size: getMarkerSize(event.severity as SeverityLevel),
        affectedPopulation: event.affectedPopulation || 0,
        country: event.location.country || "",
        isNew: newIds.has(event.id),
      },
    });
  }
  return { type: "FeatureCollection", features };
}

/** Add the clustered event source, its layers and interactions to a map */
export function addEventLayers(
  map: MapLibreMap,
  { getEvents, onSelect }: { getEvents: () => DisasterEvent[]; onSelect: (event: DisasterEvent) => void },
): void {
    map.addSource("events", {
      type: "geojson",
      data: eventsToGeoJSON(getEvents()),
      cluster: true,
      clusterMaxZoom: 14,
      clusterRadius: 50,
      clusterProperties: {
        maxSev: ["max", ["get", "sevRank"]],
      },
    });
    const colors = readSeverityColors();
    const pointColor = severityColorExpression("sevRank", colors);

    map.addLayer({
      id: "clusters",
      type: "circle",
      source: "events",
      filter: ["has", "point_count"],
      layout: {
        // Clusters holding severe events are drawn above the others
        "circle-sort-key": ["get", "maxSev"],
      },
      paint: {
        "circle-color": severityColorExpression("maxSev", colors),
        "circle-radius": ["step", ["get", "point_count"], 16, 10, 21, 50, 27],
        "circle-stroke-color": "#ffffff",
        "circle-stroke-width": 2,
      },
    });

    map.addLayer({
      id: "cluster-count",
      type: "symbol",
      source: "events",
      filter: ["has", "point_count"],
      layout: {
        "text-field": ["get", "point_count_abbreviated"],
        "text-font": LABEL_FONT,
        "text-size": 13,
        "symbol-sort-key": ["get", "maxSev"],
      },
      paint: {
        // A dark halo keeps the count readable on every severity colour
        "text-color": "#ffffff",
        "text-halo-color": "rgba(10, 17, 29, 0.75)",
        "text-halo-width": 1.4,
      },
    });

    map.addLayer({
      id: "events-layer",
      type: "circle",
      source: "events",
      filter: ["!", ["has", "point_count"]],
      layout: {
        "circle-sort-key": ["get", "sevRank"],
      },
      paint: {
        "circle-radius": ["get", "size"],
        "circle-color": pointColor,
        "circle-stroke-color": "#ffffff",
        "circle-stroke-width": 2,
        "circle-opacity": 0.95,
      },
    });

    // Event type icon on each marker; images are added asynchronously below
    map.addLayer({
      id: "events-icon",
      type: "symbol",
      source: "events",
      filter: ["!", ["has", "point_count"]],
      layout: {
        "icon-image": ["get", "icon"],
        "icon-size": ["match", ["get", "sevRank"], 3, 0.66, 2, 0.58, 0.5],
        "icon-allow-overlap": true,
        "icon-ignore-placement": true,
        "symbol-sort-key": ["get", "sevRank"],
      },
    });
    void addEventTypeIcons(map);

    map.addLayer({
      id: "events-pulse",
      type: "circle",
      source: "events",
      filter: [
        "all",
        ["!", ["has", "point_count"]],
        ["==", ["get", "severity"], "critical"],
      ],
      paint: {
        "circle-radius": [
          "interpolate",
          ["linear"],
          ["get", "size"],
          6,
          12,
          12,
          20,
        ],
        "circle-color": pointColor,
        "circle-opacity": 0.3,
        "circle-stroke-width": 0,
      },
    });

    // Radius and opacity are driven per frame by useNewEventPulse
    map.addLayer({
      id: NEW_EVENTS_LAYER,
      type: "circle",
      source: "events",
      filter: ["all", ["!", ["has", "point_count"]], ["==", ["get", "isNew"], true]],
      paint: {
        "circle-radius": ["+", ["get", "size"], 6],
        "circle-color": "rgba(0,0,0,0)",
        "circle-stroke-color": pointColor,
        "circle-stroke-width": 2,
        "circle-stroke-opacity": 0.9,
      },
    });

    // Severity colours follow the light/dark theme (a class on <html>)
    const themeObserver = new MutationObserver(() => applySeverityColors(map));
    themeObserver.observe(document.documentElement, { attributes: true, attributeFilter: ["class"] });
    map.once("remove", () => themeObserver.disconnect());

    map.on("click", "clusters", async (e) => {
      const mapInstance = map;

      const features = mapInstance.queryRenderedFeatures(e.point, {
        layers: ["clusters"],
      });
      const feature = features[0];
      if (!feature) return;

      const clusterId = feature.properties?.cluster_id as
        | number
        | undefined;
      if (clusterId === undefined) return;

      const source = mapInstance.getSource("events") as
        | GeoJSONSource
        | undefined;
      if (!source) return;

      const zoom = await source.getClusterExpansionZoom(clusterId);
      const coordinates = (feature.geometry as GeoJSON.Point)
        .coordinates as [number, number];

      mapInstance.easeTo({
        center: coordinates,
        zoom: zoom,
      });
    });

    map.on("click", "events-layer", (e) => {
      const feature = e.features?.[0];
      if (!feature) return;

      const eventId = feature.properties?.id;
      const clickedEvent = getEvents().find((ev) => ev.id === eventId);
      if (clickedEvent) onSelect(clickedEvent);
    });

    map.on("mouseenter", "clusters", () => {
      if (map) {
        map.getCanvas().style.cursor = "pointer";
      }
    });

    map.on("mouseleave", "clusters", () => {
      if (map) {
        map.getCanvas().style.cursor = "";
      }
    });

    map.on("mouseenter", "events-layer", () => {
      if (map) {
        map.getCanvas().style.cursor = "pointer";
      }
    });

    map.on("mouseleave", "events-layer", () => {
      if (map) {
        map.getCanvas().style.cursor = "";
      }
    });
}
