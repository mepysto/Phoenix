"use client";

import { useEffect, useRef, useState, useCallback, useMemo } from "react";
import type {
  Map as MapLibreMap,
  NavigationControl,
  ScaleControl,
  GeoJSONSource,
} from "maplibre-gl";
import type {
  ApiDisasterEvent,
  EventType,
  SeverityLevel,
} from "@/lib/api/client";
import {
  EVENT_TYPE_COLORS,
  EVENT_TYPE_LABELS,
  EVENT_TYPES,
  SEVERITY_COLORS,
} from "@phoenix/shared/constants";
import { useMapStore } from "@/store/mapStore";
import { useSettingsStore } from "@/store/settingsStore";
import { useTranslation } from "@/lib/i18n/useTranslation";
import { formatPosition, getEventPosition } from "@/lib/eventPosition";
import { applyBasemap, loadBasemapStyle, LABEL_FONT } from "@/lib/map/basemaps";
import type { MapView } from "@/lib/map/urlState";
import { useRasterOverlays } from "./useRasterOverlays";

type DisasterEvent = ApiDisasterEvent;

interface GlobeViewerProps {
  events?: DisasterEvent[];
  onEventClick?: (event: DisasterEvent) => void;
  /** Fly to this event and open its card (e.g. from a /?event=<id> link) */
  focusEvent?: DisasterEvent | null;
  /** Camera to start from (deep link); read once when the map is created */
  initialView?: MapView;
  initialProjection?: "globe" | "mercator";
  /** Called after the camera settles or the projection changes */
  onViewChange?: (view: MapView, projection: "globe" | "mercator") => void;
}

// Stable reference so effects depending on `events` do not re-run every render
const NO_EVENTS: DisasterEvent[] = [];

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

function readView(map: MapLibreMap): MapView {
  const center = map.getCenter();
  return {
    lng: center.lng,
    lat: center.lat,
    zoom: map.getZoom(),
    bearing: map.getBearing(),
    pitch: map.getPitch(),
  };
}

function eventsToGeoJSON(events: DisasterEvent[]): GeoJSON.FeatureCollection {
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

export default function GlobeViewer({
  events = NO_EVENTS,
  onEventClick,
  focusEvent,
  initialView,
  initialProjection,
  onViewChange,
}: GlobeViewerProps) {
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<MapLibreMap | null>(null);
  const maplibreRef = useRef<typeof import("maplibre-gl") | null>(null);
  const [selectedEvent, setSelectedEvent] = useState<DisasterEvent | null>(
    null,
  );
  const defaultProjection = useSettingsStore((s) => s.defaultProjection);
  const { t } = useTranslation();
  const [is3D, setIs3D] = useState(
    (initialProjection ?? defaultProjection) === "globe",
  );
  const [mapReady, setMapReady] = useState(false);
  const { basemap, toggleBasemap, layers } = useMapStore();

  const eventsRef = useRef<DisasterEvent[]>(events);
  useEffect(() => {
    eventsRef.current = events;
  }, [events]);

  // The map is created once per mount. Values the init code needs are read
  // through refs so changing them never tears down and rebuilds the map
  // (which reset the camera and left basemap/layer state unapplied).
  const onEventClickRef = useRef(onEventClick);
  useEffect(() => {
    onEventClickRef.current = onEventClick;
  }, [onEventClick]);
  const is3DRef = useRef(is3D);
  useEffect(() => {
    is3DRef.current = is3D;
  }, [is3D]);
  const initialViewRef = useRef(initialView);
  const onViewChangeRef = useRef(onViewChange);
  useEffect(() => {
    onViewChangeRef.current = onViewChange;
  }, [onViewChange]);

  useEffect(() => {
    if (!mapContainer.current || map.current) return;
    let cancelled = false;

    const initMap = async () => {
      const maplibregl = await import("maplibre-gl");
      maplibreRef.current = maplibregl;

      // Unmounted (or StrictMode's first pass cleaned up) while loading
      if (cancelled || !mapContainer.current || map.current) return;

      const currentBasemap = useMapStore.getState().basemap;
      const style = await loadBasemapStyle(currentBasemap);
      if (cancelled || !mapContainer.current || map.current) return;
      map.current = new maplibregl.Map({
        container: mapContainer.current,
        style,
        center: initialViewRef.current
          ? [initialViewRef.current.lng, initialViewRef.current.lat]
          : [0, 20],
        zoom: initialViewRef.current?.zoom ?? 2,
        bearing: initialViewRef.current?.bearing ?? 0,
        pitch: initialViewRef.current?.pitch ?? 0,
      });

      map.current.on("moveend", () => {
        if (!map.current) return;
        onViewChangeRef.current?.(
          readView(map.current),
          is3DRef.current ? "globe" : "mercator",
        );
      });

      map.current.on("load", () => {
        if (!map.current) return;

        if ("setProjection" in map.current) {
          (
            map.current as unknown as {
              setProjection: (proj: { type: string }) => void;
            }
          ).setProjection({
            type: is3DRef.current ? "globe" : "mercator",
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
            "text-font": LABEL_FONT,
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
            onEventClickRef.current?.(clickedEvent);
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

    const cancelScheduled =
      "requestIdleCallback" in window
        ? (() => {
            const id = window.requestIdleCallback(() => void initMap());
            return () => window.cancelIdleCallback(id);
          })()
        : (() => {
            const id = setTimeout(() => void initMap(), 1);
            return () => clearTimeout(id);
          })();

    return () => {
      cancelled = true;
      cancelScheduled();
      map.current?.remove();
      map.current = null;
      setMapReady(false);
    };
  }, []);

  useEffect(() => {
    if (!map.current || !mapReady || !focusEvent) return;
    const position = getEventPosition(focusEvent);
    setSelectedEvent(focusEvent);
    if (position) {
      map.current.flyTo({ center: [position.lng, position.lat], zoom: 5 });
    }
  }, [focusEvent, mapReady]);

  useEffect(() => {
    if (!map.current || !mapReady) return;

    const source = map.current.getSource("events") as GeoJSONSource | undefined;
    if (source) {
      source.setData(eventsToGeoJSON(events));
    }
  }, [events, mapReady]);

  useEffect(() => {
    if (!map.current || !mapReady) return;

    applyBasemap(map.current, basemap);
  }, [basemap, mapReady]);

  useEffect(() => {
    if (!map.current || !mapReady) return;

    const eventsLayer = layers.find((l) => l.id === "events");
    if (eventsLayer) {
      const eventsVisible = eventsLayer.visible;
      const eventsOpacity = eventsLayer.opacity;

      if (map.current.getLayer("events-layer")) {
        map.current.setLayoutProperty(
          "events-layer",
          "visibility",
          eventsVisible ? "visible" : "none",
        );
        map.current.setPaintProperty(
          "events-layer",
          "circle-opacity",
          eventsOpacity * 0.9,
        );
      }

      if (map.current.getLayer("events-pulse")) {
        map.current.setLayoutProperty(
          "events-pulse",
          "visibility",
          eventsVisible ? "visible" : "none",
        );
        map.current.setPaintProperty(
          "events-pulse",
          "circle-opacity",
          eventsOpacity * 0.3,
        );
      }

      if (map.current.getLayer("clusters")) {
        map.current.setLayoutProperty(
          "clusters",
          "visibility",
          eventsVisible ? "visible" : "none",
        );
        map.current.setPaintProperty(
          "clusters",
          "circle-opacity",
          eventsOpacity,
        );
      }

      if (map.current.getLayer("cluster-count")) {
        map.current.setLayoutProperty(
          "cluster-count",
          "visibility",
          eventsVisible ? "visible" : "none",
        );
        map.current.setPaintProperty(
          "cluster-count",
          "text-opacity",
          eventsOpacity,
        );
      }
    }

    const satelliteLayer = layers.find((l) => l.id === "satellite");
    if (satelliteLayer && map.current.getLayer("satellite-basemap")) {
      map.current.setPaintProperty(
        "satellite-basemap",
        "raster-opacity",
        satelliteLayer.opacity,
      );
    }
  }, [layers, mapReady]);

  // Only list types actually on the map, in the canonical order
  useRasterOverlays(map, mapReady);

  const legendTypes = useMemo(() => {
    const present = new Set(events.map((e) => e.type as EventType));
    return EVENT_TYPES.filter((type) => present.has(type));
  }, [events]);

  // The URL already carries camera/basemap/filters (useMapUrlState)
  const [linkCopied, setLinkCopied] = useState(false);
  const copyViewLink = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(window.location.href);
      setLinkCopied(true);
      setTimeout(() => setLinkCopied(false), 2000);
    } catch {
      // Clipboard blocked (insecure context/permissions): the address bar has it
    }
  }, []);

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
    onViewChangeRef.current?.(readView(map.current), newIs3D ? "globe" : "mercator");
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
        <button
          onClick={copyViewLink}
          className="rounded-lg bg-gray-900/90 px-3 py-2 text-sm font-medium text-white shadow-lg backdrop-blur hover:bg-gray-800 transition-colors"
        >
          <span aria-live="polite">{linkCopied ? t.map.linkCopied : t.map.share}</span>
        </button>
      </div>

      <div className="absolute bottom-4 left-4 rounded-lg bg-gray-900/90 p-3 text-xs text-gray-300 shadow-lg backdrop-blur">
        <div className="mb-2 font-medium text-white">
          {t.map.activeEvents}: {events.length}
        </div>
        {/* Markers: colour = event type, size = severity (see eventsToGeoJSON) */}
        <div className="mb-2 flex max-w-xs flex-wrap gap-x-3 gap-y-1">
          {legendTypes.map((type) => (
            <div key={type} className="flex items-center gap-1">
              <span
                className="h-2 w-2 rounded-full"
                style={{ backgroundColor: EVENT_TYPE_COLORS[type] }}
              />
              <span>{EVENT_TYPE_LABELS[type]}</span>
            </div>
          ))}
        </div>
        <div className="flex items-center gap-3">
          {(["low", "medium", "high", "critical"] as SeverityLevel[]).map(
            (severity) => (
              <div key={severity} className="flex items-center gap-1">
                <span
                  className="rounded-full bg-gray-400"
                  style={{
                    width: getMarkerSize(severity),
                    height: getMarkerSize(severity),
                  }}
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
              aria-label={t.common.close}
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
                  formatPosition(getEventPosition(selectedEvent))}
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
