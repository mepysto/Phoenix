"use client";

import "@/lib/cesium/baseUrl"; // before "cesium"
import { useEffect, useMemo, useRef, useState } from "react";
import { Viewer, Entity, PointGraphics, useCesium } from "resium";
import {
  Cartesian3,
  Color,
  Credit,
  Ion,
  ImageryLayer,
  Terrain,
  UrlTemplateImageryProvider,
  createOsmBuildingsAsync,
  type Cesium3DTileset,
} from "cesium";
import "cesium/Build/Cesium/Widgets/widgets.css";
import type { ApiDisasterEvent, EventType, SeverityLevel } from "@/lib/api/client";
import { EVENT_TYPE_COLORS } from "@phoenix/shared/constants";
import { getEventPosition } from "@/lib/eventPosition";
import { useTranslation } from "@/lib/i18n/useTranslation";
import { SATELLITE_SOURCE } from "@/lib/map/basemaps";
import { useMapStore } from "@/store/mapStore";
import { CesiumTracks } from "./CesiumTracks";
import { EventInfoPanel } from "./EventInfoPanel";

/**
 * 3D engine (G-6). Works without keys: the same satellite imagery as the 2D
 * map on a smooth globe. A free Cesium ion token (NEXT_PUBLIC_CESIUM_ION_TOKEN)
 * upgrades it with world terrain and 3D OSM buildings.
 */
const ION_TOKEN = process.env.NEXT_PUBLIC_CESIUM_ION_TOKEN || "";
if (typeof window !== "undefined") {
  Ion.defaultAccessToken = ION_TOKEN;
}

const NO_EVENTS: ApiDisasterEvent[] = [];
const MARKER_SIZE: Record<SeverityLevel, number> = { low: 10, medium: 13, high: 16, critical: 20 };

function baseLayer(): ImageryLayer {
  const url = SATELLITE_SOURCE.tiles![0]!;
  return new ImageryLayer(
    new UrlTemplateImageryProvider({
      url,
      maximumLevel: SATELLITE_SOURCE.maxzoom,
      // Shown on screen, not only in the credits popup: the imagery licence requires it
      credit: new Credit(SATELLITE_SOURCE.attribution ?? "", true),
    }),
  );
}

function Buildings() {
  const { viewer } = useCesium();
  const tileset = useRef<Cesium3DTileset | null>(null);
  useEffect(() => {
    if (!viewer || !ION_TOKEN) return;
    let cancelled = false;
    createOsmBuildingsAsync()
      .then((buildings) => {
        if (cancelled || viewer.isDestroyed()) return;
        viewer.scene.primitives.add(buildings);
        tileset.current = buildings;
      })
      .catch((error) => console.warn("OSM Buildings unavailable", error));
    return () => {
      cancelled = true;
      if (tileset.current && !viewer.isDestroyed()) viewer.scene.primitives.remove(tileset.current);
      tileset.current = null;
    };
  }, [viewer]);
  return null;
}

interface CesiumViewerProps {
  events?: ApiDisasterEvent[];
  onEventClick?: (event: ApiDisasterEvent) => void;
}

export default function CesiumViewer({ events = NO_EVENTS, onEventClick }: CesiumViewerProps) {
  const { t } = useTranslation();
  const setEngine = useMapStore((s) => s.setEngine);
  const [selected, setSelected] = useState<ApiDisasterEvent | null>(null);
  const imagery = useMemo(() => baseLayer(), []);
  const terrain = useMemo(() => (ION_TOKEN ? Terrain.fromWorldTerrain() : undefined), []);

  return (
    <div className="relative h-full w-full">
      <Viewer
        full
        baseLayer={imagery}
        terrain={terrain}
        animation={false}
        timeline={false}
        homeButton={false}
        sceneModePicker={false}
        baseLayerPicker={false}
        navigationHelpButton={false}
        fullscreenButton={false}
        geocoder={false}
        infoBox={false}
        selectionIndicator={false}
      >
        <Buildings />
        <CesiumTracks />
        {events.map((event) => {
          const position = getEventPosition(event);
          if (!position) return null;
          return (
            <Entity
              key={event.id}
              name={event.title}
              position={Cartesian3.fromDegrees(position.lng, position.lat, 0)}
              onClick={() => {
                setSelected(event);
                onEventClick?.(event);
              }}
            >
              <PointGraphics
                pixelSize={MARKER_SIZE[event.severity as SeverityLevel] ?? 13}
                color={Color.fromCssColorString(EVENT_TYPE_COLORS[event.type as EventType] ?? "#808080")}
                outlineColor={Color.WHITE}
                outlineWidth={2}
                disableDepthTestDistance={Number.POSITIVE_INFINITY}
              />
            </Entity>
          );
        })}
      </Viewer>

      <div className="absolute left-4 top-4 flex flex-col gap-2">
        <button
          type="button"
          onClick={() => setEngine("maplibre")}
          className="rounded-lg bg-gray-900/90 px-3 py-2 text-sm font-medium text-white shadow-lg backdrop-blur transition-colors hover:bg-gray-800"
        >
          {t.map.engine2d}
        </button>
        {!ION_TOKEN && (
          <p className="max-w-[14rem] rounded-lg bg-gray-900/80 px-3 py-2 text-xs text-gray-300">{t.map.engine3dKeyless}</p>
        )}
      </div>

      {selected && <EventInfoPanel event={selected} onClose={() => setSelected(null)} />}
    </div>
  );
}
