/** Live hazard overlays: tropical cyclones, earthquake shaking, active fires. */

import type { LayerSpecification } from "maplibre-gl";
import { API_URL } from "@/lib/api/client";
import { LABEL_FONT } from "@/lib/map/basemaps";
import { TEN_MINUTES } from "../common";
import type { LayerDefinition } from "../types";

/** Saffir-Simpson colours (TD/TS, then categories 1-5) */
const SSHS_COLOR: unknown[] = [
  "match",
  ["coalesce", ["get", "saffir_simpson"], 0],
  1, "#ffffcc",
  2, "#ffe775",
  3, "#ffc140",
  4, "#ff8f20",
  5, "#ff6060",
  /* TS/TD */ "#5ebaff",
];
const kind = (value: string) => ["==", ["get", "kind"], value];
const currentPosition = ["all", kind("position"), ["==", ["coalesce", ["get", "tau_hours"], 0], 0]];

function cycloneStyleLayers(sourceId: string): LayerSpecification[] {
  return [
    {
      id: `${sourceId}-cone`,
      type: "fill",
      source: sourceId,
      filter: kind("cone"),
      paint: { "fill-color": "#ffffff", "fill-opacity": 0.12 },
    },
    {
      id: `${sourceId}-cone-outline`,
      type: "line",
      source: sourceId,
      filter: kind("cone"),
      paint: { "line-color": "#ffffff", "line-opacity": 0.6, "line-width": 1 },
    },
    {
      id: `${sourceId}-past`,
      type: "line",
      source: sourceId,
      filter: kind("past_track"),
      paint: { "line-color": "#9ca3af", "line-width": 1.5, "line-dasharray": [2, 2] },
    },
    {
      id: `${sourceId}-track`,
      type: "line",
      source: sourceId,
      filter: kind("track"),
      paint: { "line-color": "#ffffff", "line-width": 2 },
    },
    {
      id: `${sourceId}-points`,
      type: "circle",
      source: sourceId,
      filter: kind("position"),
      paint: {
        "circle-color": SSHS_COLOR,
        "circle-radius": ["case", currentPosition, 8, 4],
        "circle-stroke-color": "#111827",
        "circle-stroke-width": 1,
      },
    },
    {
      id: `${sourceId}-label`,
      type: "symbol",
      source: sourceId,
      filter: currentPosition,
      layout: {
        "text-field": [
          "concat",
          ["get", "storm_name"],
          [
            "case",
            [">", ["coalesce", ["get", "saffir_simpson"], 0], 0],
            ["concat", " · Cat ", ["to-string", ["get", "saffir_simpson"]]],
            "",
          ],
          ["case", ["has", "max_wind_kt"], ["concat", " · ", ["to-string", ["get", "max_wind_kt"]], " kt"], ""],
        ],
        "text-font": LABEL_FONT,
        "text-size": 12,
        "text-offset": [0, 1.4],
        "text-anchor": "top",
      },
      paint: { "text-color": "#ffffff", "text-halo-color": "#111827", "text-halo-width": 1.5 },
    },
  ] as LayerSpecification[];
}

const MMI_ROMAN: unknown[] = [
  "match",
  ["get", "mmi"],
  4, "IV", 5, "V", 6, "VI", 7, "VII", 8, "VIII", 9, "IX", 10, "X",
  "",
];

function shakemapStyleLayers(sourceId: string): LayerSpecification[] {
  return [
    {
      id: `${sourceId}-contours`,
      type: "line",
      source: sourceId,
      layout: { "line-join": "round", "line-cap": "round" },
      paint: {
        // USGS's own intensity palette, carried on each contour
        "line-color": ["coalesce", ["get", "color"], "#ffff00"],
        "line-width": ["interpolate", ["linear"], ["get", "mmi"], 4, 1, 8, 4],
      },
    },
    {
      id: `${sourceId}-labels`,
      type: "symbol",
      source: sourceId,
      // Label whole-intensity contours only (4.5, 5.5 ... are unlabelled)
      filter: ["==", ["%", ["get", "mmi"], 1], 0],
      layout: {
        "symbol-placement": "line",
        "text-field": ["concat", "MMI ", MMI_ROMAN],
        "text-font": LABEL_FONT,
        "text-size": 11,
      },
      paint: { "text-color": "#ffffff", "text-halo-color": "#111827", "text-halo-width": 1.5 },
    },
  ] as LayerSpecification[];
}

export const HAZARDS_LAYERS: LayerDefinition[] = [
  {
    id: "cyclones",
    kind: "geojson",
    category: "hazards",
    auth: "keyless",
    source: {
      name: "NOAA National Hurricane Center",
      url: "https://www.nhc.noaa.gov/gis/",
      license: "U.S. Government public domain",
      commercialUse: true,
      attribution: "Tropical cyclones: NOAA NHC",
    },
    defaultOpacity: 1,
    refreshMs: TEN_MINUTES,
    loadData: async () => {
      // Aggregated and cached by the API (NHC splits storms across 15 layers)
      const response = await fetch(`${API_URL}/api/v1/hazards/cyclones`);
      if (!response.ok) throw new Error(`Cyclones ${response.status}`);
      return (await response.json()) as GeoJSON.FeatureCollection;
    },
    styleLayers: cycloneStyleLayers,
  },
  {
    id: "shakemaps",
    kind: "geojson",
    category: "hazards",
    auth: "keyless",
    source: {
      name: "USGS ShakeMap",
      url: "https://earthquake.usgs.gov/data/shakemap/",
      license: "U.S. Government public domain",
      commercialUse: true,
      attribution: "Shaking intensity: USGS ShakeMap",
    },
    defaultOpacity: 0.9,
    refreshMs: TEN_MINUTES,
    loadData: async () => {
      const response = await fetch(`${API_URL}/api/v1/hazards/shakemaps`);
      if (!response.ok) throw new Error(`ShakeMaps ${response.status}`);
      return (await response.json()) as GeoJSON.FeatureCollection;
    },
    styleLayers: shakemapStyleLayers,
  },
  {
    id: "fires",
    kind: "geojson",
    category: "hazards",
    auth: "keyless",
    source: {
      name: "NASA LANCE FIRMS",
      url: "https://www.earthdata.nasa.gov/data/tools/firms",
      license: "NASA open data; LANCE citation and disclaimer apply",
      commercialUse: true,
      attribution:
        'Active fires: <a href="https://www.earthdata.nasa.gov/data/tools/firms">NASA LANCE FIRMS</a>',
    },
    defaultOpacity: 0.9,
    refreshMs: TEN_MINUTES * 3,
    viewportDriven: true,
    minZoom: 1,
    loadData: async ({ bbox: [west, south, east, north] }) => {
      const params = new URLSearchParams({
        min_lng: String(west),
        min_lat: String(south),
        max_lng: String(east),
        max_lat: String(north),
        limit: "3000",
      });
      const response = await fetch(`${API_URL}/api/v1/hazards/fires?${params}`);
      if (!response.ok) throw new Error(`Fires ${response.status}`);
      return (await response.json()) as GeoJSON.FeatureCollection;
    },
    styleLayers: (sourceId) => [
      {
        id: `${sourceId}-points`,
        type: "circle",
        source: sourceId,
        paint: {
          // Fire radiative power (MW): small agricultural burns -> major wildfires
          "circle-color": [
            "interpolate", ["linear"], ["coalesce", ["get", "frp"], 0],
            0, "#fde047", 10, "#fb923c", 50, "#ef4444", 200, "#7f1d1d",
          ],
          "circle-radius": [
            "interpolate", ["linear"], ["zoom"],
            2, ["interpolate", ["linear"], ["coalesce", ["get", "frp"], 0], 0, 1.5, 200, 4],
            10, ["interpolate", ["linear"], ["coalesce", ["get", "frp"], 0], 0, 4, 200, 10],
          ],
          "circle-blur": 0.3,
        },
      } as LayerSpecification,
    ],
  },
];
