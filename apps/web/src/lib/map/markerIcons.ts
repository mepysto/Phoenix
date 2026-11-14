import { createElement } from "react";
import { flushSync } from "react-dom";
import { createRoot } from "react-dom/client";
import type { Map as MapLibreMap } from "maplibre-gl";
import { EVENT_TYPES } from "@phoenix/shared/constants";
import { EVENT_TYPE_ICONS } from "@/lib/eventTypeIcons";

/** Rasterised at 2x so icons stay sharp on high-density screens */
const ICON_PIXELS = 48;
const ICON_PIXEL_RATIO = 2;

export function eventTypeImageId(type: string): string {
  return `event-type-${type}`;
}

/** SVG markup of each type icon, drawn white to sit on a severity-coloured marker */
export function renderEventTypeSvgs(): Map<string, string> {
  const host = document.createElement("div");
  const root = createRoot(host);
  const svgs = new Map<string, string>();
  try {
    for (const type of EVENT_TYPES) {
      flushSync(() =>
        root.render(
          createElement(EVENT_TYPE_ICONS[type], {
            size: ICON_PIXELS,
            color: "#ffffff",
            strokeWidth: 2.5,
            "aria-hidden": true,
          }),
        ),
      );
      const svg = host.querySelector("svg");
      if (!svg) continue;
      svg.setAttribute("xmlns", "http://www.w3.org/2000/svg");
      svgs.set(type, svg.outerHTML);
    }
  } finally {
    root.unmount();
  }
  return svgs;
}

function loadSvg(svg: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const image = new Image(ICON_PIXELS, ICON_PIXELS);
    image.onload = () => resolve(image);
    image.onerror = () => reject(new Error("Could not rasterise an event type icon"));
    image.src = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
  });
}

/**
 * Register one map image per event type for the `events-icon` layer.
 * A failed icon leaves its markers as plain severity circles.
 */
export async function addEventTypeIcons(map: MapLibreMap): Promise<void> {
  const svgs = renderEventTypeSvgs();
  let removed = false;
  map.once("remove", () => {
    removed = true;
  });
  await Promise.all(
    [...svgs].map(async ([type, svg]) => {
      const id = eventTypeImageId(type);
      if (map.hasImage(id)) return;
      try {
        const image = await loadSvg(svg);
        // The map may have been removed, or the icon added, while loading
        if (!removed && !map.hasImage(id)) {
          map.addImage(id, image, { pixelRatio: ICON_PIXEL_RATIO });
        }
      } catch (error) {
        console.warn(error);
      }
    }),
  );
}
