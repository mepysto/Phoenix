"use client";

import { useMapStore } from "@/store/mapStore";
import { CameraViewer } from "./CameraViewer";

const text = (value: unknown) => (typeof value === "string" ? value : null);
const number = (value: unknown) => (typeof value === "number" ? value : null);

/** Details card for the clicked feature of an inspectable overlay */
export function FeatureInspector() {
  const inspected = useMapStore((s) => s.inspected);
  const setInspected = useMapStore((s) => s.setInspected);
  if (!inspected) return null;

  const { layerId, properties } = inspected;
  if (layerId === "cameras" && text(properties.id)) {
    return (
      <CameraViewer
        id={text(properties.id)!}
        name={text(properties.name) ?? "Camera"}
        direction={text(properties.direction)}
        source={text(properties.source)}
        snapshotMinutes={number(properties.snapshot_minutes)}
        onClose={() => setInspected(null)}
      />
    );
  }
  return null;
}
