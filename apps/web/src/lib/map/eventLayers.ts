/**
 * Disaster event markers on the MapLibre map: GeoJSON conversion and the
 * clustered source with its layers and click/hover handlers.
 */
import type { GeoJSONSource, Map as MapLibreMap } from "maplibre-gl";
import { EVENT_TYPE_COLORS } from "@phoenix/shared/constants";
import type { ApiDisasterEvent, EventType, SeverityLevel } from "@/lib/api/client";
import { getEventPosition } from "@/lib/eventPosition";
import { LABEL_FONT } from "@/lib/map/basemaps";
import type { MapView } from "@/lib/map/urlState";

type DisasterEvent = ApiDisasterEvent;

function getMarkerColor(event: DisasterEvent): string {
  return EVENT_TYPE_COLORS[event.type as EventType] || "#808080";
}

export function getMarkerSize(severity: SeverityLevel): number {
  const sizes: Record<SeverityLevel, number> = {
    low: 6,
    medium: 8,
    high: 10,
    critical: 12,
  };
  return sizes[severity] || 8;
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

export function eventsToGeoJSON(events: DisasterEvent[]): GeoJSON.FeatureCollection {
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
        severity: event.severity,
        color: getMarkerColor(event),
        size: getMarkerSize(event.severity as SeverityLevel),
        affectedPopulation: event.affectedPopulation || 0,
        country: event.location.country || "",
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
    });

    map.addLayer({
      id: "clusters",
      type: "circle",
      source: "events",
      filter: ["has", "point_count"],
      paint: {
        "circle-color": [
          "step",
          ["get", "point_count"],
          "#51bbd6",
          10,
          "#f1f075",
          50,
          "#f28cb1",
        ],
        "circle-radius": [
          "step",
          ["get", "point_count"],
          20,
          10,
          30,
          50,
          40,
        ],
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
        "text-size": 12,
      },
      paint: {
        "text-color": "#ffffff",
      },
    });

    map.addLayer({
      id: "events-layer",
      type: "circle",
      source: "events",
      filter: ["!", ["has", "point_count"]],
      paint: {
        "circle-radius": ["get", "size"],
        "circle-color": ["get", "color"],
        "circle-stroke-color": "#ffffff",
        "circle-stroke-width": 2,
        "circle-opacity": 0.9,
      },
    });

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
        "circle-color": ["get", "color"],
        "circle-opacity": 0.3,
        "circle-stroke-width": 0,
      },
    });

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
