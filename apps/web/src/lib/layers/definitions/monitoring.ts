/** Monitoring overlays (M5-M7): satellites, aircraft, ships, cameras, launches. */

import type { LayerSpecification } from "maplibre-gl";
import { API_URL } from "@/lib/api/client";
import { LABEL_FONT } from "@/lib/map/basemaps";
import { bboxCenter, bboxRadiusKm } from "@/lib/map/geo";
import { withViewsheds } from "@/lib/map/viewshed";
import type { LayerDefinition } from "../types";

export const MONITORING_LAYERS: LayerDefinition[] = [
  {
    id: "satellites",
    kind: "geojson",
    category: "monitoring",
    auth: "keyless",
    source: {
      name: "CelesTrak",
      url: "https://celestrak.org/NORAD/elements/",
      // No published licence; GP data originates from the US Space Force
      license: "No explicit licence (CelesTrak usage policy)",
      commercialUse: false,
      attribution: 'Satellite orbits: <a href="https://celestrak.org">CelesTrak</a>',
    },
    defaultOpacity: 1,
    // Positions are computed server-side from cached orbits; LEO moves ~230 km in 30 s
    refreshMs: 30_000,
    inspectable: true,
    loadData: async () => {
      const response = await fetch(`${API_URL}/api/v1/tracks/satellites`);
      if (!response.ok) throw new Error(`Satellites ${response.status}`);
      return (await response.json()) as GeoJSON.FeatureCollection;
    },
    styleLayers: (sourceId) => [
      {
        id: `${sourceId}-points`,
        type: "circle",
        source: sourceId,
        paint: {
          "circle-color": "#38bdf8",
          "circle-radius": ["interpolate", ["linear"], ["zoom"], 1, 2.5, 6, 5],
          "circle-stroke-color": "#0c4a6e",
          "circle-stroke-width": 1,
        },
      } as LayerSpecification,
      {
        id: `${sourceId}-labels`,
        type: "symbol",
        source: sourceId,
        minzoom: 3,
        layout: {
          "text-field": ["get", "name"],
          "text-font": LABEL_FONT,
          "text-size": 10,
          "text-offset": [0, 1],
          "text-anchor": "top",
        },
        paint: { "text-color": "#bae6fd", "text-halo-color": "#0f172a", "text-halo-width": 1.2 },
      } as LayerSpecification,
    ],
  },
  {
    id: "aircraft",
    kind: "geojson",
    category: "monitoring",
    auth: "keyless",
    source: {
      name: "adsb.lol",
      url: "https://adsb.lol",
      license: "ODbL",
      commercialUse: true,
      attribution: 'Aircraft: <a href="https://adsb.lol">adsb.lol</a> (ODbL)',
    },
    defaultOpacity: 1,
    refreshMs: 15_000,
    viewportDriven: true,
    // One upstream query covers at most 250 NM, about a zoom-5 view
    minZoom: 5,
    inspectable: true,
    loadData: async ({ bbox }) => {
      const { lat, lng } = bboxCenter(bbox);
      const radiusNm = Math.min(250, Math.ceil(bboxRadiusKm(bbox) / 1.852));
      const params = new URLSearchParams({ lat: lat.toFixed(3), lng: lng.toFixed(3), radius_nm: String(radiusNm) });
      const response = await fetch(`${API_URL}/api/v1/tracks/aircraft?${params}`);
      if (!response.ok) throw new Error(`Aircraft ${response.status}`);
      return (await response.json()) as GeoJSON.FeatureCollection;
    },
    styleLayers: (sourceId) => [
      {
        id: `${sourceId}-icons`,
        type: "symbol",
        source: sourceId,
        layout: {
          // Heading arrow; aircraft without a track are drawn pointing north
          "text-field": "▲",
          "text-font": LABEL_FONT,
          "text-size": ["interpolate", ["linear"], ["zoom"], 5, 10, 10, 16],
          "text-rotate": ["coalesce", ["get", "track_deg"], 0],
          "text-rotation-alignment": "map",
          "text-allow-overlap": true,
          "text-ignore-placement": true,
        },
        paint: {
          "text-color": [
            "case",
            ["get", "military"], "#fb923c",
            ["get", "on_ground"], "#94a3b8",
            "#f1f5f9",
          ],
          "text-halo-color": "#0f172a",
          "text-halo-width": 1,
        },
      } as LayerSpecification,
      {
        id: `${sourceId}-labels`,
        type: "symbol",
        source: sourceId,
        minzoom: 8,
        layout: {
          "text-field": ["coalesce", ["get", "callsign"], ""],
          "text-font": LABEL_FONT,
          "text-size": 10,
          "text-offset": [0, 1.2],
          "text-anchor": "top",
        },
        paint: { "text-color": "#cbd5e1", "text-halo-color": "#0f172a", "text-halo-width": 1.2 },
      } as LayerSpecification,
    ],
  },
  {
    id: "vessels",
    kind: "geojson",
    category: "monitoring",
    // Needs AISSTREAM_API_KEY on the server; without it the API returns an empty list
    auth: "free_key",
    source: {
      name: "AISStream",
      url: "https://aisstream.io",
      license: "AISStream terms (no explicit licence)",
      commercialUse: false,
      attribution: 'Ships: <a href="https://aisstream.io">AISStream</a>',
    },
    defaultOpacity: 1,
    refreshMs: 15_000,
    viewportDriven: true,
    minZoom: 4,
    inspectable: true,
    loadData: async ({ bbox: [west, south, east, north] }) => {
      const params = new URLSearchParams({
        min_lng: String(west),
        min_lat: String(south),
        max_lng: String(east),
        max_lat: String(north),
      });
      const response = await fetch(`${API_URL}/api/v1/tracks/vessels?${params}`);
      if (!response.ok) throw new Error(`Vessels ${response.status}`);
      return (await response.json()) as GeoJSON.FeatureCollection;
    },
    styleLayers: (sourceId) => [
      {
        id: `${sourceId}-icons`,
        type: "symbol",
        source: sourceId,
        layout: {
          "text-field": "▲",
          "text-font": LABEL_FONT,
          "text-size": ["interpolate", ["linear"], ["zoom"], 4, 9, 10, 14],
          // Heading when reported, else course over ground
          "text-rotate": ["coalesce", ["get", "heading_deg"], ["get", "course_deg"], 0],
          "text-rotation-alignment": "map",
          "text-allow-overlap": true,
          "text-ignore-placement": true,
        },
        paint: { "text-color": "#2dd4bf", "text-halo-color": "#042f2e", "text-halo-width": 1 },
      } as LayerSpecification,
      {
        id: `${sourceId}-labels`,
        type: "symbol",
        source: sourceId,
        minzoom: 8,
        layout: {
          "text-field": ["coalesce", ["get", "name"], ""],
          "text-font": LABEL_FONT,
          "text-size": 10,
          "text-offset": [0, 1.2],
          "text-anchor": "top",
        },
        paint: { "text-color": "#99f6e4", "text-halo-color": "#042f2e", "text-halo-width": 1.2 },
      } as LayerSpecification,
    ],
  },
  {
    id: "cameras",
    kind: "geojson",
    category: "monitoring",
    auth: "keyless",
    source: {
      name: "Caltrans",
      url: "https://cwwp2.dot.ca.gov/documentation/cctv/cctv.htm",
      license: "Public domain",
      commercialUse: true,
      attribution: 'Cameras: <a href="https://cwwp2.dot.ca.gov">Caltrans</a>',
    },
    defaultOpacity: 1,
    viewportDriven: true,
    minZoom: 5,
    inspectable: true,
    loadData: async ({ bbox: [west, south, east, north] }) => {
      const params = new URLSearchParams({
        min_lng: String(west),
        min_lat: String(south),
        max_lng: String(east),
        max_lat: String(north),
      });
      const response = await fetch(`${API_URL}/api/v1/cameras?${params}`);
      if (!response.ok) throw new Error(`Cameras ${response.status}`);
      // Approximate coverage wedges drawn under the camera points
      return withViewsheds((await response.json()) as GeoJSON.FeatureCollection);
    },
    styleLayers: (sourceId) => [
      {
        id: `${sourceId}-viewsheds`,
        type: "fill",
        source: sourceId,
        minzoom: 12,
        filter: ["==", ["get", "kind"], "viewshed"],
        paint: { "fill-color": "#a78bfa", "fill-opacity": 0.18, "fill-outline-color": "#a78bfa" },
      } as LayerSpecification,
      {
        id: `${sourceId}-points`,
        type: "circle",
        source: sourceId,
        filter: ["==", ["geometry-type"], "Point"],
        paint: {
          "circle-color": "#a78bfa",
          "circle-radius": ["interpolate", ["linear"], ["zoom"], 5, 2.5, 12, 6],
          "circle-stroke-color": "#1e1b4b",
          "circle-stroke-width": 1,
        },
      } as LayerSpecification,
    ],
  },
  {
    id: "launches",
    kind: "geojson",
    category: "monitoring",
    auth: "keyless",
    source: {
      name: "Launch Library 2",
      url: "https://thespacedevs.com/llapi",
      license: "Free API; credit The Space Devs",
      commercialUse: false,
      attribution: 'Launches: <a href="https://thespacedevs.com">The Space Devs</a>',
    },
    defaultOpacity: 1,
    refreshMs: 30 * 60_000,
    inspectable: true,
    loadData: async () => {
      const response = await fetch(`${API_URL}/api/v1/tracks/launches`);
      if (!response.ok) throw new Error(`Launches ${response.status}`);
      return (await response.json()) as GeoJSON.FeatureCollection;
    },
    styleLayers: (sourceId) => [
      {
        id: `${sourceId}-points`,
        type: "circle",
        source: sourceId,
        paint: {
          "circle-color": "#f472b6",
          "circle-radius": ["interpolate", ["linear"], ["zoom"], 1, 4, 8, 8],
          "circle-stroke-color": "#500724",
          "circle-stroke-width": 1.5,
        },
      } as LayerSpecification,
      {
        id: `${sourceId}-labels`,
        type: "symbol",
        source: sourceId,
        minzoom: 4,
        layout: {
          "text-field": ["get", "name"],
          "text-font": LABEL_FONT,
          "text-size": 10,
          "text-offset": [0, 1.2],
          "text-anchor": "top",
          "text-max-width": 14,
        },
        paint: { "text-color": "#fbcfe8", "text-halo-color": "#0f172a", "text-halo-width": 1.2 },
      } as LayerSpecification,
    ],
  },
];
