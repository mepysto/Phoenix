"use client";

import { useEffect } from "react";
import { useCesium } from "resium";
import {
  Cartesian2,
  Cartesian3,
  Cartographic,
  Color,
  DistanceDisplayCondition,
  LabelCollection,
  LabelStyle,
  Math as CesiumMath,
  PointPrimitiveCollection,
  type Viewer,
} from "cesium";
import { API_URL } from "@/lib/api/client";
import { useMapStore } from "@/store/mapStore";

const FEET_TO_M = 0.3048;
const NM_TO_KM = 1.852;
const MAX_AIRCRAFT_RADIUS_NM = 250;

interface Track {
  lng: number;
  lat: number;
  altitudeM: number;
  label: string | null;
  color: Color;
}

type Loader = (viewer: Viewer) => Promise<Track[]>;

const loadSatellites: Loader = async () => {
  const response = await fetch(`${API_URL}/api/v1/tracks/satellites`);
  if (!response.ok) throw new Error(`Satellites ${response.status}`);
  const data = (await response.json()) as GeoJSON.FeatureCollection<GeoJSON.Point>;
  return data.features.map((f) => ({
    lng: f.geometry.coordinates[0]!,
    lat: f.geometry.coordinates[1]!,
    altitudeM: Number(f.properties?.altitude_km ?? 700) * 1000,
    label: (f.properties?.name as string) ?? null,
    color: Color.fromCssColorString("#38bdf8"),
  }));
};

/** Aircraft around the point under the camera, within what the camera can see */
const loadAircraft: Loader = async (viewer) => {
  const camera = Cartographic.fromCartesian(viewer.camera.positionWC);
  const lat = CesiumMath.toDegrees(camera.latitude);
  const lng = CesiumMath.toDegrees(camera.longitude);
  const radiusNm = Math.min(MAX_AIRCRAFT_RADIUS_NM, Math.max(25, camera.height / 1000 / NM_TO_KM));
  const params = new URLSearchParams({ lat: lat.toFixed(3), lng: lng.toFixed(3), radius_nm: String(Math.round(radiusNm)) });
  const response = await fetch(`${API_URL}/api/v1/tracks/aircraft?${params}`);
  if (!response.ok) throw new Error(`Aircraft ${response.status}`);
  const data = (await response.json()) as GeoJSON.FeatureCollection<GeoJSON.Point>;
  return data.features.map((f) => {
    const p = f.properties ?? {};
    return {
      lng: f.geometry.coordinates[0]!,
      lat: f.geometry.coordinates[1]!,
      altitudeM: p.on_ground ? 0 : Number(p.altitude_ft ?? 0) * FEET_TO_M,
      label: (p.callsign as string) ?? null,
      color: Color.fromCssColorString(p.military ? "#fb923c" : "#f1f5f9"),
    };
  });
};

/** One overlay drawn in 3D at real altitude, refreshed while its layer is on */
function useTrackLayer(viewer: Viewer | undefined, visible: boolean, load: Loader, refreshMs: number, labelRangeM: number) {
  useEffect(() => {
    if (!viewer || !visible) return;
    const points = viewer.scene.primitives.add(new PointPrimitiveCollection()) as PointPrimitiveCollection;
    const labels = viewer.scene.primitives.add(new LabelCollection()) as LabelCollection;
    let cancelled = false;

    const draw = async () => {
      let tracks: Track[];
      try {
        tracks = await load(viewer);
      } catch (error) {
        console.warn("3D track layer refresh failed", error);
        return; // keep what is drawn
      }
      if (cancelled || viewer.isDestroyed()) return;
      points.removeAll();
      labels.removeAll();
      for (const track of tracks) {
        const position = Cartesian3.fromDegrees(track.lng, track.lat, track.altitudeM);
        points.add({ position, pixelSize: 6, color: track.color, outlineColor: Color.BLACK, outlineWidth: 1 });
        if (track.label) {
          labels.add({
            position,
            text: track.label,
            font: "11px sans-serif",
            fillColor: Color.WHITE,
            outlineColor: Color.BLACK,
            outlineWidth: 2,
            style: LabelStyle.FILL_AND_OUTLINE,
            pixelOffset: new Cartesian2(0, -12),
            distanceDisplayCondition: new DistanceDisplayCondition(0, labelRangeM),
          });
        }
      }
    };

    void draw();
    const timer = setInterval(() => void draw(), refreshMs);
    return () => {
      cancelled = true;
      clearInterval(timer);
      if (!viewer.isDestroyed()) {
        viewer.scene.primitives.remove(points);
        viewer.scene.primitives.remove(labels);
      }
    };
  }, [viewer, visible, load, refreshMs, labelRangeM]);
}

/**
 * Satellites and aircraft in 3D at their real altitude (G-16). Follows the
 * layer panel's switches for the same overlays as the 2D map.
 */
export function CesiumTracks() {
  const { viewer } = useCesium();

  useEffect(() => {
    if (!viewer || process.env.NODE_ENV === "production") return;
    // Debug/E2E handle (dev builds only), like window.__phoenixMap for 2D
    (window as unknown as { __phoenixCesium?: Viewer }).__phoenixCesium = viewer;
  }, [viewer]);
  const satellitesOn = useMapStore((s) => s.layers.some((l) => l.id === "satellites" && l.visible));
  const aircraftOn = useMapStore((s) => s.layers.some((l) => l.id === "aircraft" && l.visible));

  useTrackLayer(viewer, satellitesOn, loadSatellites, 30_000, 3_000_000);
  useTrackLayer(viewer, aircraftOn, loadAircraft, 15_000, 150_000);
  return null;
}
