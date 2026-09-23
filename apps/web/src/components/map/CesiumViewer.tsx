"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Viewer, Entity, PointGraphics, useCesium } from "resium";
import {
  Cartesian3,
  Ion,
  Color,
  Terrain,
  Cesium3DTileset,
  createOsmBuildingsAsync,
  Viewer as CesiumViewerType,
} from "cesium";
import "cesium/Build/Cesium/Widgets/widgets.css";
import type {
  ApiDisasterEvent,
  EventType,
  SeverityLevel,
} from "@/lib/api/client";
import { EVENT_TYPE_COLORS, SEVERITY_COLORS } from "@phoenix/shared/constants";
import { escapeHtml } from "@/lib/escapeHtml";

if (typeof window !== "undefined") {
  Ion.defaultAccessToken = process.env.NEXT_PUBLIC_CESIUM_ION_TOKEN || "";
}

type DisasterEvent = ApiDisasterEvent;

interface CesiumViewerProps {
  events?: DisasterEvent[];
  onEventClick?: (event: DisasterEvent) => void;
  showTerrain?: boolean;
  showBuildings?: boolean;
}

// Stable reference so effects depending on `events` do not re-run every render
const NO_EVENTS: DisasterEvent[] = [];

function getMarkerColor(event: DisasterEvent): Color {
  const hexColor = EVENT_TYPE_COLORS[event.type as EventType] || "#808080";
  return Color.fromCssColorString(hexColor);
}

function getMarkerSize(severity: SeverityLevel): number {
  const sizes: Record<SeverityLevel, number> = {
    low: 12,
    medium: 16,
    high: 20,
    critical: 24,
  };
  return sizes[severity] || 16;
}

function BuildingsLoader({ showBuildings }: { showBuildings: boolean }) {
  const { viewer } = useCesium();
  const buildingsRef = useRef<Cesium3DTileset | null>(null);

  useEffect(() => {
    if (!viewer || !showBuildings) {
      if (buildingsRef.current && viewer) {
        viewer.scene.primitives.remove(buildingsRef.current);
        buildingsRef.current = null;
      }
      return;
    }

    const loadBuildings = async () => {
      try {
        const osmBuildingsTileset = await createOsmBuildingsAsync();
        viewer.scene.primitives.add(osmBuildingsTileset);
        buildingsRef.current = osmBuildingsTileset;
      } catch (error) {
        console.error("Failed to load OSM Buildings:", error);
      }
    };

    loadBuildings();

    return () => {
      if (buildingsRef.current && viewer) {
        viewer.scene.primitives.remove(buildingsRef.current);
        buildingsRef.current = null;
      }
    };
  }, [viewer, showBuildings]);

  return null;
}

export default function CesiumViewer({
  events = NO_EVENTS,
  onEventClick,
  showTerrain = true,
  showBuildings = false,
}: CesiumViewerProps) {
  const [selectedEvent, setSelectedEvent] = useState<DisasterEvent | null>(
    null,
  );
  const viewerRef = useRef<CesiumViewerType | null>(null);

  const terrain = useMemo(() => {
    if (showTerrain) {
      return Terrain.fromWorldTerrain();
    }
    return undefined;
  }, [showTerrain]);

  const handleEventClick = useCallback(
    (event: DisasterEvent) => {
      setSelectedEvent(event);
      onEventClick?.(event);
    },
    [onEventClick],
  );

  return (
    <div className="relative h-full w-full">
      <Viewer
        full
        terrain={terrain}
        animation={false}
        timeline={false}
        homeButton={false}
        sceneModePicker={true}
        baseLayerPicker={false}
        navigationHelpButton={false}
        fullscreenButton={false}
        geocoder={false}
        ref={(e) => {
          if (e?.cesiumElement) {
            viewerRef.current = e.cesiumElement;
          }
        }}
      >
        <BuildingsLoader showBuildings={showBuildings} />
        {events.map((event) => (
          <Entity
            key={event.id}
            name={event.title}
            description={`
              <div style="padding: 8px; min-width: 200px;">
                <p style="margin: 0 0 8px 0; font-size: 13px; color: #333;">${escapeHtml(event.description || "")}</p>
                <div style="display: flex; align-items: center; gap: 8px; margin-top: 8px;">
                  <span style="padding: 2px 8px; border-radius: 9999px; font-size: 11px; background: ${SEVERITY_COLORS[event.severity as SeverityLevel] ?? "#808080"}; color: white;">
                    ${escapeHtml(event.severity.toUpperCase())}
                  </span>
                  ${event.affectedPopulation ? `<span style="font-size: 11px; color: #666;">${event.affectedPopulation.toLocaleString()} affected</span>` : ""}
                </div>
                <div style="margin-top: 8px; font-size: 11px; color: #666;">
                  Location: ${event.location.country ? escapeHtml(event.location.country) : `${event.location.lat.toFixed(2)}, ${event.location.lng.toFixed(2)}`}
                </div>
              </div>
            `}
            position={Cartesian3.fromDegrees(
              event.location.lng,
              event.location.lat,
              0,
            )}
            onClick={() => handleEventClick(event)}
          >
            <PointGraphics
              pixelSize={getMarkerSize(event.severity as SeverityLevel)}
              color={getMarkerColor(event)}
              outlineColor={Color.WHITE}
              outlineWidth={2}
              disableDepthTestDistance={Number.POSITIVE_INFINITY}
            />
          </Entity>
        ))}
      </Viewer>

      <div className="absolute bottom-4 left-4 rounded-lg bg-gray-900/90 p-3 text-xs text-gray-300 shadow-lg backdrop-blur">
        <div className="mb-2 font-medium text-white">
          Active Events: {events.length}
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
              <span className="text-gray-500">Location</span>
              <span className="text-gray-300">
                {selectedEvent.location.country ||
                  `${selectedEvent.location.lat.toFixed(2)}, ${selectedEvent.location.lng.toFixed(2)}`}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Severity</span>
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
                <span className="text-gray-500">Affected</span>
                <span className="text-gray-300">
                  {selectedEvent.affectedPopulation.toLocaleString()} people
                </span>
              </div>
            )}
          </div>
        </div>
      )}

      <div className="absolute left-4 top-4 flex flex-col gap-2">
        <div className="rounded-lg bg-gray-900/90 px-3 py-2 text-sm font-medium text-white shadow-lg backdrop-blur">
          {showTerrain ? "3D Terrain: ON" : "3D Terrain: OFF"}
        </div>
        {showBuildings && (
          <div className="rounded-lg bg-gray-900/90 px-3 py-2 text-sm font-medium text-white shadow-lg backdrop-blur">
            OSM Buildings: ON
          </div>
        )}
      </div>
    </div>
  );
}
