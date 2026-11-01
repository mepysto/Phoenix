"use client";

import { useEffect, useRef } from "react";
import * as maplibregl from "maplibre-gl";
import { DARK_STYLE_URL } from "@/lib/map/basemaps";
import { configureMaplibreWorker } from "@/lib/map/maplibreWorker";
import { SPHERE, type ItemKind, type PlanItem } from "@/lib/sphere";

configureMaplibreWorker(maplibregl);

export const KIND_COLORS: Record<ItemKind, string> = {
  tent: "#c9d3e2",
  tap: "#38bdf8",
  toilet: "#a78bfa",
  health: "#34d0ac",
  distribution: "#f5b83d",
};

// Used when the basemap style cannot be fetched (offline, blocked, slow
// field links): the plan still works on a plain background with the scale.
const FALLBACK_STYLE: maplibregl.StyleSpecification = {
  version: 8,
  sources: {},
  layers: [
    { id: "bg", type: "background", paint: { "background-color": "#111a2b" } },
  ],
};

const KIND_RADIUS: Record<ItemKind, number> = {
  tent: 4,
  tap: 6,
  toilet: 5,
  health: 8,
  distribution: 8,
};

/** Circle polygon of radius m around a point, for walking-reach rings */
function ring(
  lat: number,
  lng: number,
  m: number,
  steps = 40,
): [number, number][] {
  const out: [number, number][] = [];
  const dLat = m / 111_195;
  const dLng = m / (111_195 * Math.cos((lat * Math.PI) / 180));
  for (let i = 0; i <= steps; i++) {
    const a = (i / steps) * 2 * Math.PI;
    out.push([lng + dLng * Math.cos(a), lat + dLat * Math.sin(a)]);
  }
  return out;
}

interface PlanMapProps {
  center: { lat: number; lng: number };
  items: PlanItem[];
  showReach: boolean;
  /** Placing or removing; null = just look */
  onMapClick: (lat: number, lng: number) => void;
  onItemClick: (id: string) => void;
  cursor: string;
  /** Change to fit the view to all items (after an automatic layout) */
  fitSignal?: number;
}

export default function PlanMap({
  center,
  items,
  showReach,
  onMapClick,
  onItemClick,
  cursor,
  fitSignal,
}: PlanMapProps) {
  const el = useRef<HTMLDivElement>(null);
  const map = useRef<maplibregl.Map | null>(null);
  const ready = useRef(false);
  // Latest data to draw; run once the style has loaded
  const applyData = useRef<(() => void) | null>(null);
  const handlers = useRef({ onMapClick, onItemClick });
  handlers.current = { onMapClick, onItemClick };

  useEffect(() => {
    if (!el.current || map.current) return;
    const m = new maplibregl.Map({
      container: el.current,
      style: DARK_STYLE_URL,
      center: [center.lng, center.lat],
      zoom: 15,
    });
    m.addControl(
      new maplibregl.NavigationControl({ showCompass: false }),
      "top-right",
    );
    m.addControl(
      new maplibregl.ScaleControl({ unit: "metric" }),
      "bottom-right",
    );
    let styleOk = false;
    const fallback = window.setTimeout(() => {
      if (!styleOk) m.setStyle(FALLBACK_STYLE);
    }, 8000);
    m.on("error", () => {
      if (!styleOk) {
        window.clearTimeout(fallback);
        m.setStyle(FALLBACK_STYLE);
      }
    });
    m.once("style.load", () => {
      styleOk = true;
      window.clearTimeout(fallback);
      const empty = { type: "FeatureCollection" as const, features: [] };
      m.addSource("plan-reach", { type: "geojson", data: empty });
      m.addSource("plan-items", { type: "geojson", data: empty });
      m.addLayer({
        id: "plan-reach-line",
        type: "line",
        source: "plan-reach",
        paint: {
          "line-color": ["get", "color"],
          "line-opacity": 0.55,
          "line-width": 1.2,
          "line-dasharray": [2, 2],
        },
      });
      m.addLayer({
        id: "plan-items",
        type: "circle",
        source: "plan-items",
        paint: {
          "circle-color": ["get", "color"],
          "circle-radius": [
            "interpolate",
            ["linear"],
            ["zoom"],
            13,
            ["*", ["get", "r"], 0.5],
            17,
            ["*", ["get", "r"], 1.6],
          ],
          "circle-stroke-color": "#0a111d",
          "circle-stroke-width": 1.5,
        },
      });
      m.on("click", (e) => {
        const hit = m.queryRenderedFeatures(e.point, {
          layers: ["plan-items"],
        })[0];
        if (hit?.properties?.id)
          handlers.current.onItemClick(String(hit.properties.id));
        else handlers.current.onMapClick(e.lngLat.lat, e.lngLat.lng);
      });
      ready.current = true;
      applyData.current?.();
    });
    map.current = m;
    return () => {
      m.remove();
      map.current = null;
      ready.current = false;
    };
    // Created once; recentred below
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    map.current?.jumpTo({ center: [center.lng, center.lat] });
  }, [center.lat, center.lng]);

  useEffect(() => {
    const m = map.current;
    if (!m) return;
    const apply = () => {
      const items_ = m.getSource("plan-items") as
        maplibregl.GeoJSONSource | undefined;
      const reach = m.getSource("plan-reach") as
        maplibregl.GeoJSONSource | undefined;
      items_?.setData({
        type: "FeatureCollection",
        features: items.map((i) => ({
          type: "Feature",
          geometry: { type: "Point", coordinates: [i.lng, i.lat] },
          properties: {
            id: i.id,
            kind: i.kind,
            color: KIND_COLORS[i.kind],
            r: KIND_RADIUS[i.kind],
          },
        })),
      });
      reach?.setData({
        type: "FeatureCollection",
        features: showReach
          ? items
              // Water reach only: 50 m toilet rings would cover a dense site
              .filter((i) => i.kind === "tap")
              .map((i) => ({
                type: "Feature" as const,
                geometry: {
                  type: "Polygon" as const,
                  coordinates: [ring(i.lat, i.lng, SPHERE.waterMaxDistanceM)],
                },
                properties: { color: KIND_COLORS[i.kind] },
              }))
          : [],
      });
    };
    applyData.current = apply;
    if (ready.current) apply();
  }, [items, showReach]);

  useEffect(() => {
    const m = map.current;
    if (!m || !fitSignal || items.length === 0) return;
    const bounds = new maplibregl.LngLatBounds();
    for (const i of items) bounds.extend([i.lng, i.lat]);
    m.fitBounds(bounds, { padding: 60, maxZoom: 17, duration: 800 });
    // Only when asked, not on every edit
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fitSignal]);

  useEffect(() => {
    const canvas = map.current?.getCanvas();
    if (canvas) canvas.style.cursor = cursor;
  }, [cursor]);

  return <div ref={el} className="h-full w-full" />;
}
