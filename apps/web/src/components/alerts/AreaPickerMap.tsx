"use client";

import { useEffect, useRef } from "react";
import * as maplibregl from "maplibre-gl";
import { configureMaplibreWorker } from "@/lib/map/maplibreWorker";
import { vectorStyleUrl } from "@/lib/map/basemaps";

configureMaplibreWorker(maplibregl);

const SOURCE = "alert-area";
const EARTH_RADIUS_KM = 6371;

/** A circle of radiusKm around a point, as a polygon (64 steps) */
export function circlePolygon(lat: number, lng: number, radiusKm: number, steps = 64): GeoJSON.Feature<GeoJSON.Polygon> {
  const coords: [number, number][] = [];
  const d = radiusKm / EARTH_RADIUS_KM;
  const lat1 = (lat * Math.PI) / 180;
  const lng1 = (lng * Math.PI) / 180;
  for (let i = 0; i < steps; i++) {
    const bearing = (2 * Math.PI * i) / steps;
    const lat2 = Math.asin(Math.sin(lat1) * Math.cos(d) + Math.cos(lat1) * Math.sin(d) * Math.cos(bearing));
    const lng2 =
      lng1 + Math.atan2(Math.sin(bearing) * Math.sin(d) * Math.cos(lat1), Math.cos(d) - Math.sin(lat1) * Math.sin(lat2));
    coords.push([(lng2 * 180) / Math.PI, (lat2 * 180) / Math.PI]);
  }
  coords.push(coords[0]!); // GeoJSON rings close on exactly the first point
  return { type: "Feature", properties: {}, geometry: { type: "Polygon", coordinates: [coords] } };
}

/**
 * Pick an alert area by clicking a small map (UX plan 5.4): no coordinates
 * to type. Shows the chosen point and the alert radius around it.
 */
export default function AreaPickerMap({
  lat,
  lng,
  radiusKm,
  label,
  onPick,
}: {
  lat: number | null;
  lng: number | null;
  radiusKm: number;
  label: string;
  onPick: (lat: number, lng: number) => void;
}) {
  const container = useRef<HTMLDivElement>(null);
  const map = useRef<maplibregl.Map | null>(null);
  const marker = useRef<maplibregl.Marker | null>(null);
  const onPickRef = useRef(onPick);
  onPickRef.current = onPick;

  useEffect(() => {
    if (!container.current || map.current) return;
    const m = new maplibregl.Map({
      container: container.current,
      style: vectorStyleUrl(),
      center: [lng ?? 20, lat ?? 15],
      zoom: lat !== null ? 4 : 1,
      // An (i) button: full credits would cover much of a map this small
      attributionControl: { compact: true },
    });
    m.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
    m.getCanvas().style.cursor = "crosshair";
    m.on("click", (e) => onPickRef.current(Number(e.lngLat.lat.toFixed(2)), Number(e.lngLat.lng.toFixed(2))));
    m.on("load", () => {
      m.addSource(SOURCE, { type: "geojson", data: { type: "FeatureCollection", features: [] } });
      m.addLayer({ id: `${SOURCE}-fill`, type: "fill", source: SOURCE, paint: { "fill-color": "#34d0ac", "fill-opacity": 0.15 } });
      m.addLayer({ id: `${SOURCE}-line`, type: "line", source: SOURCE, paint: { "line-color": "#34d0ac", "line-width": 2 } });
    });
    map.current = m;
    return () => {
      marker.current?.remove();
      m.remove();
      map.current = null;
    };
    // Created once; position updates are applied below
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const m = map.current;
    if (!m || lat === null || lng === null) return;
    // A marker must have a position before it joins the map
    if (!marker.current) marker.current = new maplibregl.Marker({ color: "#34d0ac" }).setLngLat([lng, lat]).addTo(m);
    else marker.current.setLngLat([lng, lat]);
    const draw = () => (m.getSource(SOURCE) as maplibregl.GeoJSONSource | undefined)?.setData(circlePolygon(lat, lng, radiusKm));
    if (m.isStyleLoaded()) draw();
    else m.once("load", draw);
  }, [lat, lng, radiusKm]);

  return <div ref={container} role="application" aria-label={label} className="h-56 w-full overflow-hidden rounded-lg" />;
}
