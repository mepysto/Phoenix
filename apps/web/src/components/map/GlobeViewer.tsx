"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import type {
  Map as MapLibreMap,
  NavigationControl,
  ScaleControl,
  GeoJSONSource,
} from "maplibre-gl";
import type {
  DisasterEvent,
  SeverityLevel,
  EventType,
} from "@phoenix/shared/types";
import { EVENT_TYPE_COLORS, SEVERITY_COLORS } from "@phoenix/shared/constants";
import { useMapStore } from "@/store/mapStore";
import { useSettingsStore } from "@/store/settingsStore";
import { useTranslation } from "@/lib/i18n/useTranslation";

interface GlobeViewerProps {
  events?: DisasterEvent[];
  onEventClick?: (event: DisasterEvent) => void;
}

const MOCK_EVENTS: DisasterEvent[] = [
  {
    id: "1",
    type: "earthquake",
    title: "M 6.2 Earthquake - Turkey",
    description: "Moderate earthquake struck southeastern Turkey",
    location: { lat: 37.5, lng: 37.0, country: "Turkey", countryCode: "TR" },
    severity: "high",
    affectedPopulation: 50000,
    startDate: new Date().toISOString(),
    isActive: true,
    sources: [],
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  },
  {
    id: "2",
    type: "flood",
    title: "Severe Flooding - Bangladesh",
    description: "Monsoon flooding affecting multiple districts",
    location: {
      lat: 23.8,
      lng: 90.4,
      country: "Bangladesh",
      countryCode: "BD",
    },
    severity: "critical",
    affectedPopulation: 200000,
    startDate: new Date().toISOString(),
    isActive: true,
    sources: [],
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  },
  {
    id: "3",
    type: "wildfire",
    title: "Wildfire - California, USA",
    description: "Large wildfire burning in northern California",
    location: {
      lat: 39.5,
      lng: -121.5,
      country: "United States",
      countryCode: "US",
    },
    severity: "high",
    affectedPopulation: 10000,
    startDate: new Date().toISOString(),
    isActive: true,
    sources: [],
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  },
  {
    id: "4",
    type: "hurricane",
    title: "Tropical Cyclone - Philippines",
    description: "Category 4 typhoon approaching eastern coast",
    location: {
      lat: 14.5,
      lng: 126.0,
      country: "Philippines",
      countryCode: "PH",
    },
    severity: "critical",
    affectedPopulation: 500000,
    startDate: new Date().toISOString(),
    isActive: true,
    sources: [],
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  },
  {
    id: "5",
    type: "war",
    title: "Armed Conflict - Ukraine",
    description: "Ongoing military operations in eastern regions",
    location: { lat: 48.5, lng: 37.5, country: "Ukraine", countryCode: "UA" },
    severity: "critical",
    affectedPopulation: 1000000,
    startDate: new Date().toISOString(),
    isActive: true,
    sources: [],
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  },
];

function getMarkerColor(event: DisasterEvent): string {
  return EVENT_TYPE_COLORS[event.type as EventType] || "#808080";
}

function getMarkerSize(severity: SeverityLevel): number {
  const sizes: Record<SeverityLevel, number> = {
    low: 6,
    medium: 8,
    high: 10,
    critical: 12,
  };
  return sizes[severity] || 8;
}

function eventsToGeoJSON(events: DisasterEvent[]): GeoJSON.FeatureCollection {
  return {
    type: "FeatureCollection",
    features: events.map((event) => ({
      type: "Feature" as const,
      geometry: {
        type: "Point" as const,
        coordinates: [event.location.lng, event.location.lat],
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
    })),
  };
}

export default function GlobeViewer({
  events = MOCK_EVENTS,
  onEventClick,
}: GlobeViewerProps) {
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<MapLibreMap | null>(null);
  const maplibreRef = useRef<typeof import("maplibre-gl") | null>(null);
  const [selectedEvent, setSelectedEvent] = useState<DisasterEvent | null>(
    null,
  );
  const { defaultProjection, defaultBasemap } = useSettingsStore();
  const { t } = useTranslation();
  const [is3D, setIs3D] = useState(defaultProjection === "globe");
  const [mapReady, setMapReady] = useState(false);
  const { basemap, toggleBasemap, setBasemap } = useMapStore();

  useEffect(() => {
    setBasemap(defaultBasemap);
  }, [defaultBasemap, setBasemap]);

  const eventsRef = useRef<DisasterEvent[]>(events);
  useEffect(() => {
    eventsRef.current = events;
  }, [events]);

  useEffect(() => {
    if (!mapContainer.current || map.current) return;

    const initMap = async () => {
      const maplibregl = await import("maplibre-gl");
      maplibreRef.current = maplibregl;

      if (!mapContainer.current) return;

      const currentBasemap = useMapStore.getState().basemap;
      map.current = new maplibregl.Map({
        container: mapContainer.current,
        style: {
          version: 8,
          sources: {
            dark: {
              type: "raster",
              tiles: [
                "https://a.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}@2x.png",
                "https://b.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}@2x.png",
                "https://c.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}@2x.png",
              ],
              tileSize: 256,
              attribution: "&copy; OpenStreetMap contributors, &copy; CARTO",
            },
            satellite: {
              type: "raster",
              tiles: [
                "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
              ],
              tileSize: 256,
              maxzoom: 19,
              attribution: "Esri, Maxar, Earthstar Geographics",
            },
          },
          layers: [
            {
              id: "dark-basemap",
              type: "raster",
              source: "dark",
              minzoom: 0,
              maxzoom: 19,
              layout: {
                visibility: currentBasemap === "dark" ? "visible" : "none",
              },
            },
            {
              id: "satellite-basemap",
              type: "raster",
              source: "satellite",
              minzoom: 0,
              maxzoom: 19,
              layout: {
                visibility: currentBasemap === "satellite" ? "visible" : "none",
              },
            },
          ],
          glyphs: "https://demotiles.maplibre.org/font/{fontstack}/{range}.pbf",
        },
        center: [0, 20],
        zoom: 2,
      });

      map.current.on("load", () => {
        if (!map.current) return;

        if ("setProjection" in map.current) {
          (
            map.current as unknown as {
              setProjection: (proj: { type: string }) => void;
            }
          ).setProjection({
            type: is3D ? "globe" : "mercator",
          });
        }

        if (map.current.getSource("events")) {
          setMapReady(true);
          return;
        }

        map.current.addSource("events", {
          type: "geojson",
          data: eventsToGeoJSON(eventsRef.current),
          cluster: true,
          clusterMaxZoom: 14,
          clusterRadius: 50,
        });

        map.current.addLayer({
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

        map.current.addLayer({
          id: "cluster-count",
          type: "symbol",
          source: "events",
          filter: ["has", "point_count"],
          layout: {
            "text-field": ["get", "point_count_abbreviated"],
            "text-size": 12,
          },
          paint: {
            "text-color": "#ffffff",
          },
        });

        map.current.addLayer({
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

        map.current.addLayer({
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

        map.current.on("click", "clusters", async (e) => {
          const mapInstance = map.current;
          if (!mapInstance) return;

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

        map.current.on("click", "events-layer", (e) => {
          const feature = e.features?.[0];
          if (!feature) return;

          const eventId = feature.properties?.id;
          const clickedEvent = eventsRef.current.find(
            (ev) => ev.id === eventId,
          );

          if (clickedEvent) {
            setSelectedEvent(clickedEvent);
            onEventClick?.(clickedEvent);
          }
        });

        map.current.on("mouseenter", "clusters", () => {
          if (map.current) {
            map.current.getCanvas().style.cursor = "pointer";
          }
        });

        map.current.on("mouseleave", "clusters", () => {
          if (map.current) {
            map.current.getCanvas().style.cursor = "";
          }
        });

        map.current.on("mouseenter", "events-layer", () => {
          if (map.current) {
            map.current.getCanvas().style.cursor = "pointer";
          }
        });

        map.current.on("mouseleave", "events-layer", () => {
          if (map.current) {
            map.current.getCanvas().style.cursor = "";
          }
        });

        setMapReady(true);
      });

      map.current.addControl(
        new maplibregl.NavigationControl() as NavigationControl,
        "top-right",
      );
      map.current.addControl(
        new maplibregl.ScaleControl({
          maxWidth: 100,
          unit: "metric",
        }) as ScaleControl,
        "bottom-right",
      );
    };

    if ("requestIdleCallback" in window) {
      window.requestIdleCallback(() => initMap());
    } else {
      setTimeout(initMap, 1);
    }

    return () => {
      map.current?.remove();
      map.current = null;
    };
  }, [is3D, onEventClick]);

  useEffect(() => {
    if (!map.current || !mapReady) return;

    const source = map.current.getSource("events") as GeoJSONSource | undefined;
    if (source) {
      source.setData(eventsToGeoJSON(events));
    }
  }, [events, mapReady]);

  useEffect(() => {
    if (!map.current || !mapReady) return;

    map.current.setLayoutProperty(
      "dark-basemap",
      "visibility",
      basemap === "dark" ? "visible" : "none",
    );
    map.current.setLayoutProperty(
      "satellite-basemap",
      "visibility",
      basemap === "satellite" ? "visible" : "none",
    );
  }, [basemap, mapReady]);

  const toggleProjection = useCallback(() => {
    if (!map.current) return;
    const newIs3D = !is3D;
    setIs3D(newIs3D);
    if ("setProjection" in map.current) {
      (
        map.current as unknown as {
          setProjection: (proj: { type: string }) => void;
        }
      ).setProjection({
        type: newIs3D ? "globe" : "mercator",
      });
    }
  }, [is3D]);

  return (
    <div className="relative h-full w-full">
      {!mapReady && (
        <div className="absolute inset-0 flex items-center justify-center bg-gray-900">
          <div className="text-center">
            <div className="mb-4 h-12 w-12 animate-spin rounded-full border-4 border-primary-500 border-t-transparent mx-auto" />
            <p className="text-gray-400">{t.map.initializingGlobe}</p>
          </div>
        </div>
      )}

      <div ref={mapContainer} className="h-full w-full" />

      <div className="absolute left-4 top-4 flex flex-col gap-2">
        <button
          onClick={toggleProjection}
          className="rounded-lg bg-gray-900/90 px-3 py-2 text-sm font-medium text-white shadow-lg backdrop-blur hover:bg-gray-800 transition-colors"
        >
          {is3D ? t.map.view2d : t.map.globe3d}
        </button>
        <button
          onClick={toggleBasemap}
          className="rounded-lg bg-gray-900/90 px-3 py-2 text-sm font-medium text-white shadow-lg backdrop-blur hover:bg-gray-800 transition-colors"
        >
          {basemap === "dark" ? t.map.satellite : t.map.dark}
        </button>
      </div>

      <div className="absolute bottom-4 left-4 rounded-lg bg-gray-900/90 p-3 text-xs text-gray-300 shadow-lg backdrop-blur">
        <div className="mb-2 font-medium text-white">
          {t.map.activeEvents}: {events.length}
        </div>
        <div className="flex flex-wrap gap-2">
          {(["critical", "high", "medium", "low"] as SeverityLevel[]).map(
            (severity) => (
              <div key={severity} className="flex items-center gap-1">
                <span
                  className="h-2 w-2 rounded-full"
                  style={{ backgroundColor: SEVERITY_COLORS[severity] }}
                />
                <span className="capitalize">{severity}</span>
              </div>
            ),
          )}
        </div>
      </div>

      {selectedEvent && (
        <div className="absolute right-4 top-4 w-80 rounded-lg bg-gray-900/95 p-4 shadow-xl backdrop-blur">
          <div className="mb-2 flex items-start justify-between">
            <h3 className="font-semibold text-white">{selectedEvent.title}</h3>
            <button
              onClick={() => setSelectedEvent(null)}
              className="text-gray-400 hover:text-white"
            >
              &times;
            </button>
          </div>
          <p className="mb-3 text-sm text-gray-400">
            {selectedEvent.description}
          </p>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-500">{t.events.location}</span>
              <span className="text-gray-300">
                {selectedEvent.location.country ||
                  `${selectedEvent.location.lat.toFixed(2)}, ${selectedEvent.location.lng.toFixed(2)}`}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">{t.events.severity}</span>
              <span
                className="rounded-full px-2 py-0.5 text-xs font-medium text-white"
                style={{
                  backgroundColor:
                    SEVERITY_COLORS[selectedEvent.severity as SeverityLevel],
                }}
              >
                {selectedEvent.severity.toUpperCase()}
              </span>
            </div>
            {selectedEvent.affectedPopulation && (
              <div className="flex justify-between">
                <span className="text-gray-500">{t.events.affected}</span>
                <span className="text-gray-300">
                  {selectedEvent.affectedPopulation.toLocaleString()}
                </span>
              </div>
            )}
          </div>
        </div>
      )}

      <style jsx global>{`
        @keyframes pulse {
          0%,
          100% {
            opacity: 1;
            transform: scale(1);
          }
          50% {
            opacity: 0.7;
            transform: scale(1.1);
          }
        }
      `}</style>
    </div>
  );
}
