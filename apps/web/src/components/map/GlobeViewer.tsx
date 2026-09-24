"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import type {
  Map as MapLibreMap,
  NavigationControl,
  ScaleControl,
  GeoJSONSource,
} from "maplibre-gl";
import type { ApiDisasterEvent } from "@/lib/api/client";
import { useMapStore } from "@/store/mapStore";
import { useSettingsStore } from "@/store/settingsStore";
import { useTranslation } from "@/lib/i18n/useTranslation";
import { getEventPosition } from "@/lib/eventPosition";
import { applyBasemap, loadBasemapStyle } from "@/lib/map/basemaps";
import type { MapView } from "@/lib/map/urlState";
import { currentViewport } from "@/lib/map/viewport";
import { setMapInstance } from "@/lib/map/mapInstance";
import { addEventLayers, eventsToGeoJSON, readView } from "@/lib/map/eventLayers";
import { viewModeFilter } from "@/lib/map/viewModes";
import { EventInfoPanel } from "./EventInfoPanel";
import { MapControls } from "./MapControls";
import { MapLegend } from "./MapLegend";
import { ViewModeFilters } from "./ViewModeFilters";
import { useMapOverlays } from "./useMapOverlays";

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
  // Per-field selectors: the store also carries the viewport, which changes on every move
  const basemap = useMapStore((s) => s.basemap);
  const layers = useMapStore((s) => s.layers);
  const viewMode = useMapStore((s) => s.viewMode);

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
        // Collapsed to an (i) button: with several overlays the credits would cover the legend and timeline
        attributionControl: { compact: true },
        center: initialViewRef.current
          ? [initialViewRef.current.lng, initialViewRef.current.lat]
          : [0, 20],
        zoom: initialViewRef.current?.zoom ?? 2,
        bearing: initialViewRef.current?.bearing ?? 0,
        pitch: initialViewRef.current?.pitch ?? 0,
      });

      map.current.on("moveend", () => {
        if (!map.current) return;
        useMapStore.getState().setViewport(currentViewport(map.current));
        onViewChangeRef.current?.(
          readView(map.current),
          is3DRef.current ? "globe" : "mercator",
        );
      });

      map.current.on("load", () => {
        if (!map.current) return;
        useMapStore.getState().setViewport(currentViewport(map.current));

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

        addEventLayers(map.current, {
          getEvents: () => eventsRef.current,
          onSelect: (clickedEvent) => {
            setSelectedEvent(clickedEvent);
            onEventClickRef.current?.(clickedEvent);
          },
        });

        if (process.env.NODE_ENV !== "production") {
          // Debug/E2E handle (dev builds only): window.__phoenixMap.getStyle() etc.
          (window as unknown as { __phoenixMap?: MapLibreMap }).__phoenixMap = map.current;
        }
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

  // Share the ready map with tools that draw their own layers (route planner)
  useEffect(() => {
    if (!mapReady || !map.current) return;
    setMapInstance(map.current);
    return () => setMapInstance(null);
  }, [mapReady]);

  // Sensor view mode: filter only the map image, not MapLibre's controls
  useEffect(() => {
    if (!map.current || !mapReady) return;
    map.current.getCanvasContainer().style.filter = viewModeFilter(viewMode) ?? "";
  }, [viewMode, mapReady]);

  // Camera moves requested from outside the map (Disaster Brief scenes)
  const cameraRequest = useMapStore((s) => s.cameraRequest);
  useEffect(() => {
    if (!map.current || !mapReady || !cameraRequest) return;
    const { lng, lat, zoom, bearing, pitch } = cameraRequest.view;
    map.current.flyTo({ center: [lng, lat], zoom, bearing, pitch, duration: 3000, essential: true });
  }, [cameraRequest, mapReady]);

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

  useMapOverlays(map, mapReady);


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

      <ViewModeFilters />
      <div ref={mapContainer} className="h-full w-full" />
      {viewMode === "crt" && (
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-0"
          style={{
            background:
              "repeating-linear-gradient(0deg, rgba(0,0,0,0.25) 0 1px, transparent 1px 3px), radial-gradient(ellipse at center, transparent 60%, rgba(0,0,0,0.45) 100%)",
          }}
        />
      )}

      <MapControls is3D={is3D} onToggleProjection={toggleProjection} />

      <MapLegend events={events} />

      {selectedEvent && (
        <EventInfoPanel event={selectedEvent} onClose={() => setSelectedEvent(null)} />
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
