"use client";

import { useEffect, useRef } from "react";
import * as maplibregl from "maplibre-gl";
import { SEVERITY_COLORS } from "@phoenix/shared/constants";
import { eventsAPI, type SeverityLevel } from "@/lib/api/client";
import { getEventPosition } from "@/lib/eventPosition";
import { escapeHtml } from "@/lib/escapeHtml";
import { DARK_STYLE_URL } from "@/lib/map/basemaps";
import { configureMaplibreWorker } from "@/lib/map/maplibreWorker";

configureMaplibreWorker(maplibregl);

const ORDER: SeverityLevel[] = ["low", "medium", "high", "critical"];

interface EmbedMapProps {
  minSeverity: SeverityLevel;
  center: [number, number];
  zoom: number;
  origin: string;
  openLabel: string;
}

/** The live map for third-party pages: events only, links open Phoenix. */
export default function EmbedMap({
  minSeverity,
  center,
  zoom,
  origin,
  openLabel,
}: EmbedMapProps) {
  const el = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!el.current) return;
    const map = new maplibregl.Map({
      container: el.current,
      style: DARK_STYLE_URL,
      center,
      zoom,
      attributionControl: { compact: true },
    });
    map.addControl(
      new maplibregl.NavigationControl({ showCompass: false }),
      "top-right",
    );
    let timer: ReturnType<typeof setInterval> | undefined;

    const load = async () => {
      const severities = ORDER.slice(ORDER.indexOf(minSeverity));
      const res = await eventsAPI.list({ isActive: true, severities }, 500);
      const features = res.data.flatMap((e) => {
        const p = getEventPosition(e);
        if (!p) return [];
        return [
          {
            type: "Feature" as const,
            geometry: { type: "Point" as const, coordinates: [p.lng, p.lat] },
            properties: {
              id: e.id,
              title: e.title,
              color: SEVERITY_COLORS[e.severity as SeverityLevel] ?? "#888",
              r: 4 + ORDER.indexOf(e.severity as SeverityLevel) * 2,
            },
          },
        ];
      });
      const data = { type: "FeatureCollection" as const, features };
      const src = map.getSource("events") as
        maplibregl.GeoJSONSource | undefined;
      if (src) src.setData(data);
      else {
        map.addSource("events", { type: "geojson", data });
        map.addLayer({
          id: "events",
          type: "circle",
          source: "events",
          paint: {
            "circle-color": ["get", "color"],
            "circle-radius": ["get", "r"],
            "circle-stroke-color": "#0a111d",
            "circle-stroke-width": 1.5,
            "circle-opacity": 0.9,
          },
        });
      }
    };

    map.on("load", () => {
      void load().catch(() => {});
      // Embeds stay open for hours on news pages: refresh every 5 minutes
      timer = setInterval(() => void load().catch(() => {}), 300_000);
    });
    map.on("click", "events", (e) => {
      const f = e.features?.[0];
      if (!f) return;
      const { id, title } = f.properties as { id: string; title: string };
      new maplibregl.Popup({ closeButton: true, maxWidth: "260px" })
        .setLngLat(e.lngLat)
        .setHTML(
          `<strong>${escapeHtml(title)}</strong><br/><a href="${origin}/events/${encodeURIComponent(id)}" target="_blank" rel="noopener">${escapeHtml(openLabel)}</a>`,
        )
        .addTo(map);
    });
    map.on(
      "mouseenter",
      "events",
      () => (map.getCanvas().style.cursor = "pointer"),
    );
    map.on("mouseleave", "events", () => (map.getCanvas().style.cursor = ""));
    return () => {
      if (timer) clearInterval(timer);
      map.remove();
    };
  }, [minSeverity, center, zoom, origin, openLabel]);

  return <div ref={el} className="h-full w-full" />;
}
