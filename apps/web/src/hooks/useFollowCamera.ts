"use client";

import { useEffect } from "react";
import { getMapInstance } from "@/lib/map/mapInstance";
import { useMapStore } from "@/store/mapStore";
import { useUiStore } from "@/store/uiStore";

const FOLLOW_DRIFT_PX = 20;

/**
 * Follow mode (G-16, 2D): keep the camera on a tracked aircraft or ship and
 * keep its card current as the overlay refreshes.
 */
export function useFollowCamera(): void {
  const follow = useUiStore((s) => s.follow);

  useEffect(() => {
    const map = getMapInstance();
    if (!follow || !map) return;
    const sourceId = `overlay-${follow.layerId}`;
    const update = () => {
      if (!map.getSource(sourceId)) return;
      const [feature] = map.querySourceFeatures(sourceId, { filter: ["==", ["get", follow.key], follow.value] });
      if (!feature || feature.geometry.type !== "Point") return;
      const [lng, lat] = feature.geometry.coordinates as [number, number];
      // Moving refreshes viewport-driven overlays, which fires sourcedata again:
      // only move when the target has drifted, so following does not loop
      const target = map.project([lng, lat]);
      const canvas = map.getCanvas();
      const drift = Math.hypot(target.x - canvas.clientWidth / 2, target.y - canvas.clientHeight / 2);
      if (drift > FOLLOW_DRIFT_PX) map.easeTo({ center: [lng, lat], duration: 1000 });
      const { inspected, setInspected } = useMapStore.getState();
      if (inspected?.layerId === follow.layerId) {
        setInspected({ layerId: follow.layerId, properties: feature.properties ?? {}, lng, lat });
      }
    };
    const onData = (e: { sourceId?: string; isSourceLoaded?: boolean }) => {
      if (e.sourceId === sourceId && e.isSourceLoaded) update();
    };
    update();
    map.on("sourcedata", onData);
    return () => {
      map.off("sourcedata", onData);
    };
  }, [follow]);
}
