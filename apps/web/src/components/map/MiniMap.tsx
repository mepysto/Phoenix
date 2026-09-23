"use client";

import { useEffect, useRef } from "react";
import maplibregl from "maplibre-gl";
import { createBasemapStyle } from "@/lib/map/basemaps";

interface MiniMapProps {
  lat: number;
  lng: number;
  zoom?: number;
}

export default function MiniMap({ lat, lng, zoom = 8 }: MiniMapProps) {
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<maplibregl.Map | null>(null);
  const marker = useRef<maplibregl.Marker | null>(null);

  useEffect(() => {
    if (!mapContainer.current || map.current) return;

    map.current = new maplibregl.Map({
      container: mapContainer.current,
      style: createBasemapStyle("dark"),
      center: [lng, lat],
      zoom: zoom,
      interactive: true,
    });

    map.current.addControl(
      new maplibregl.NavigationControl({ showCompass: false }),
      "top-right",
    );

    marker.current = new maplibregl.Marker({ color: "#ef4444" })
      .setLngLat([lng, lat])
      .addTo(map.current);

    return () => {
      marker.current?.remove();
      map.current?.remove();
      map.current = null;
    };
  }, [lat, lng, zoom]);

  useEffect(() => {
    if (map.current && marker.current) {
      marker.current.setLngLat([lng, lat]);
      map.current.flyTo({ center: [lng, lat], zoom: zoom });
    }
  }, [lat, lng, zoom]);

  return <div ref={mapContainer} className="h-full w-full" />;
}
