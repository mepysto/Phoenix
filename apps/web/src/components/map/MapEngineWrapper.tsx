"use client";

import dynamic from "next/dynamic";
import { useMapStore } from "@/store/mapStore";
import type { ApiDisasterEvent } from "@/lib/api/client";
import type { MapView } from "@/lib/map/urlState";
import { BrandLoader } from "@/components/ui/States";

const GlobeViewer = dynamic(() => import("./GlobeViewer"), {
  ssr: false,
  loading: () => <BrandLoader />,
});

const CesiumViewer = dynamic(() => import("./CesiumViewer"), {
  ssr: false,
  loading: () => <BrandLoader />,
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
  const engine = useMapStore((s) => s.engine);

  if (engine === "cesium") {
    return (
      <CesiumViewer events={events} onEventClick={onEventClick} />
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
