"use client";

import { useEffect, useRef } from "react";
import * as maplibregl from "maplibre-gl";
import type { ApiDamageSummary } from "@/lib/api/client";
import { DAMAGE_COLORS, type DamageGrade } from "@/lib/damage";
import { vectorStyleUrl } from "@/lib/map/basemaps";
import { configureMaplibreWorker } from "@/lib/map/maplibreWorker";

configureMaplibreWorker(maplibregl);

const FALLBACK: maplibregl.StyleSpecification = {
  version: 8,
  sources: {},
  layers: [
    { id: "bg", type: "background", paint: { "background-color": "#111a2b" } },
  ],
};

function extend(bounds: maplibregl.LngLatBounds, coords: unknown): void {
  if (Array.isArray(coords) && typeof coords[0] === "number") {
    bounds.extend([coords[0] as number, coords[1] as number]);
  } else if (Array.isArray(coords)) {
    for (const c of coords) extend(bounds, c);
  }
}

/** Assessed areas drawn by grade; fits the view to them. */
export default function DamageMap({
  areas,
}: {
  areas: ApiDamageSummary["areas"];
}) {
  const el = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!el.current || areas.length === 0) return;
    const map = new maplibregl.Map({
      container: el.current,
      style: vectorStyleUrl(),
      center: [0, 0],
      zoom: 1,
    });
    map.addControl(
      new maplibregl.NavigationControl({ showCompass: false }),
      "top-right",
    );
    let styled = false;
    const fallback = () => {
      if (!styled) map.setStyle(FALLBACK);
    };
    const timer = window.setTimeout(fallback, 8000);
    map.on("error", fallback);
    map.once("style.load", () => {
      styled = true;
      window.clearTimeout(timer);
      const features = areas.map((a) => ({
        type: "Feature" as const,
        geometry: a.geometry as unknown as GeoJSON.Geometry,
        properties: {
          color: DAMAGE_COLORS[a.grade as DamageGrade] ?? DAMAGE_COLORS.unknown,
          name: a.name ?? "",
        },
      }));
      map.addSource("damage", {
        type: "geojson",
        data: { type: "FeatureCollection", features },
      });
      map.addLayer({
        id: "damage-fill",
        type: "fill",
        source: "damage",
        filter: ["==", ["geometry-type"], "Polygon"],
        paint: { "fill-color": ["get", "color"], "fill-opacity": 0.35 },
      });
      map.addLayer({
        id: "damage-line",
        type: "line",
        source: "damage",
        filter: ["==", ["geometry-type"], "Polygon"],
        paint: { "line-color": ["get", "color"], "line-width": 1.5 },
      });
      map.addLayer({
        id: "damage-point",
        type: "circle",
        source: "damage",
        filter: ["==", ["geometry-type"], "Point"],
        paint: {
          "circle-color": ["get", "color"],
          "circle-radius": 6,
          "circle-stroke-color": "#0a111d",
          "circle-stroke-width": 1.5,
        },
      });
      const bounds = new maplibregl.LngLatBounds();
      for (const a of areas)
        extend(bounds, (a.geometry as { coordinates?: unknown }).coordinates);
      if (!bounds.isEmpty())
        map.fitBounds(bounds, { padding: 40, maxZoom: 14, duration: 0 });
    });
    return () => {
      window.clearTimeout(timer);
      map.remove();
    };
  }, [areas]);

  return <div ref={el} className="h-full w-full" />;
}
