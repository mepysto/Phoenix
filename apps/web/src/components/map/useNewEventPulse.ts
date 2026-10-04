"use client";

import { useEffect, type RefObject } from "react";
import type { Map as MapLibreMap } from "maplibre-gl";
import { NEW_EVENTS_LAYER } from "@/lib/map/eventLayers";
import { pulseFrame } from "@/lib/map/newEventPulse";
import { useMapStore } from "@/store/mapStore";

function prefersReducedMotion(): boolean {
  return typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches === true;
}

/**
 * Animate the ring around newly arrived events. The frame loop only runs while
 * there is something new to show, and follows the events layer's visibility
 * and opacity from the layer panel.
 */
export function useNewEventPulse(mapRef: RefObject<MapLibreMap | null>, mapReady: boolean, active: boolean): void {
  const eventsLayer = useMapStore((s) => s.layers.find((l) => l.id === "events"));
  const visible = eventsLayer?.visible ?? true;
  const layerOpacity = eventsLayer?.opacity ?? 1;

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapReady || !map.getLayer(NEW_EVENTS_LAYER)) return;
    map.setLayoutProperty(NEW_EVENTS_LAYER, "visibility", visible && active ? "visible" : "none");
    if (!visible || !active) return;

    const draw = (t: number) => {
      const { grow, opacity } = pulseFrame(t, reducedMotion);
      map.setPaintProperty(NEW_EVENTS_LAYER, "circle-radius", ["+", ["get", "size"], grow]);
      map.setPaintProperty(NEW_EVENTS_LAYER, "circle-stroke-opacity", opacity * layerOpacity);
    };
    const reducedMotion = prefersReducedMotion();
    if (reducedMotion) {
      draw(0);
      return;
    }
    let frame = requestAnimationFrame(function loop(t) {
      draw(t);
      frame = requestAnimationFrame(loop);
    });
    return () => cancelAnimationFrame(frame);
  }, [mapRef, mapReady, active, visible, layerOpacity]);
}
