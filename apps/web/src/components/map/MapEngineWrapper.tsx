"use client";

import dynamic from "next/dynamic";
import { useMapStore } from "@/store/mapStore";
import type { ApiDisasterEvent } from "@/lib/api/client";
import type { MapView } from "@/lib/map/urlState";

const GlobeViewer = dynamic(() => import("./GlobeViewer"), {
  ssr: false,
  loading: () => (
    <div className="flex h-full w-full items-center justify-center bg-gray-900">
      <div className="text-center">
        <div className="mb-4 h-12 w-12 animate-spin rounded-full border-4 border-blue-500 border-t-transparent mx-auto" />
        <p className="text-gray-400">Loading MapLibre Globe...</p>
      </div>
    </div>
  ),
});

const CesiumViewer = dynamic(() => import("./CesiumViewer"), {
  ssr: false,
  loading: () => (
    <div className="flex h-full w-full items-center justify-center bg-gray-900">
      <div className="text-center">
        <div className="mb-4 h-12 w-12 animate-spin rounded-full border-4 border-blue-500 border-t-transparent mx-auto" />
        <p className="text-gray-400">Loading Cesium 3D...</p>
      </div>
    </div>
  ),
});

interface MapEngineWrapperProps {
  events?: ApiDisasterEvent[];
  onEventClick?: (event: ApiDisasterEvent) => void;
  /** Event to fly to and open (deep link); MapLibre engine only for now */
  focusEvent?: ApiDisasterEvent | null;
  initialView?: MapView;
  initialProjection?: "globe" | "mercator";
  onViewChange?: (view: MapView, projection: "globe" | "mercator") => void;
}

export default function MapEngineWrapper({
  events,
  onEventClick,
  focusEvent,
  initialView,
  initialProjection,
  onViewChange,
}: MapEngineWrapperProps) {
  const { engine, viewerConfig } = useMapStore();

  if (engine === "cesium") {
    return (
      <CesiumViewer
        events={events}
        onEventClick={onEventClick}
        showTerrain={viewerConfig.terrain.enabled}
        showBuildings={viewerConfig.buildings.enabled}
      />
    );
  }

  return (
    <GlobeViewer
      events={events}
      onEventClick={onEventClick}
      focusEvent={focusEvent}
      initialView={initialView}
      initialProjection={initialProjection}
      onViewChange={onViewChange}
    />
  );
}
