/** Critical infrastructure overlays: power plants, dams, submarine cables, hospitals. */

import type { ExpressionSpecification, LayerSpecification } from "maplibre-gl";
import { API_URL } from "@/lib/api/client";
import { LABEL_FONT } from "@/lib/map/basemaps";
import type { LayerDefinition, Viewport } from "../types";

/** Viewport query against the infrastructure API */
async function loadInfrastructure(kind: "dam" | "power_plant", viewport: Viewport) {
  const [west, south, east, north] = viewport.bbox;
  const params = new URLSearchParams({
    min_lng: String(west),
    min_lat: String(south),
    max_lng: String(east),
    max_lat: String(north),
    kinds: kind,
    limit: "2000",
  });
  const response = await fetch(`${API_URL}/api/v1/infrastructure?${params}`);
  if (!response.ok) throw new Error(`Infrastructure ${response.status}`);
  return (await response.json()) as GeoJSON.FeatureCollection;
}

const INFRASTRUCTURE_LABEL = (sourceId: string, minzoom: number): LayerSpecification => ({
  id: `${sourceId}-labels`,
  type: "symbol",
  source: sourceId,
  minzoom,
  layout: {
    "text-field": ["coalesce", ["get", "name"], ""],
    "text-font": LABEL_FONT,
    "text-size": 11,
    "text-offset": [0, 1.1],
    "text-anchor": "top",
    "text-optional": true,
  },
  paint: { "text-color": "#e5e7eb", "text-halo-color": "#111827", "text-halo-width": 1.2 },
});

/** WRI primary_fuel -> colour */
const FUEL_COLOR: ExpressionSpecification = [
  "match",
  ["get", "primary_fuel"],
  "Hydro", "#3b82f6",
  "Nuclear", "#a855f7",
  "Coal", "#6b7280",
  "Gas", "#f97316",
  "Oil", "#92400e",
  "Solar", "#facc15",
  "Wind", "#2dd4bf",
  "Biomass", "#65a30d",
  "Geothermal", "#dc2626",
  "#9ca3af",
];

export const INFRASTRUCTURE_LAYERS: LayerDefinition[] = [
  {
    id: "power-plants",
    kind: "geojson",
    category: "infrastructure",
    auth: "keyless",
    source: {
      name: "WRI Global Power Plant Database",
      url: "https://datasets.wri.org/datasets/global-power-plant-database",
      license: "CC BY 4.0",
      commercialUse: true,
      attribution: "Power plants: WRI Global Power Plant Database (CC BY 4.0)",
    },
    defaultOpacity: 0.9,
    viewportDriven: true,
    minZoom: 3,
    loadData: (viewport) => loadInfrastructure("power_plant", viewport),
    styleLayers: (sourceId) => [
      {
        id: `${sourceId}-points`,
        type: "circle",
        source: sourceId,
        paint: {
          "circle-color": FUEL_COLOR,
          // Area proportional to capacity: 1 MW -> 2 px, 10 GW -> ~14 px
          "circle-radius": ["interpolate", ["linear"], ["sqrt", ["coalesce", ["get", "capacity_mw"], 1]], 1, 2, 100, 14],
          "circle-stroke-color": "#111827",
          "circle-stroke-width": 0.5,
        },
      } as LayerSpecification,
      INFRASTRUCTURE_LABEL(sourceId, 8),
    ],
  },
  {
    id: "dams",
    kind: "geojson",
    category: "infrastructure",
    auth: "keyless",
    source: {
      name: "Global Dam Watch",
      url: "https://www.globaldamwatch.org/database",
      license: "CC BY 4.0 (© European Union / GDW)",
      commercialUse: true,
      attribution: "Dams: Global Dam Watch (CC BY 4.0)",
    },
    defaultOpacity: 0.9,
    viewportDriven: true,
    minZoom: 4,
    loadData: (viewport) => loadInfrastructure("dam", viewport),
    styleLayers: (sourceId) => [
      {
        id: `${sourceId}-points`,
        type: "circle",
        source: sourceId,
        paint: {
          // Hollow rings, so dams stay distinct from hydro plants (solid blue dots)
          "circle-color": "#0f172a",
          "circle-radius": ["interpolate", ["linear"], ["coalesce", ["get", "height_m"], 10], 10, 3, 150, 8],
          "circle-stroke-color": "#22d3ee",
          "circle-stroke-width": 2,
        },
      } as LayerSpecification,
      INFRASTRUCTURE_LABEL(sourceId, 8),
    ],
  },
  {
    id: "submarine-cables",
    kind: "geojson",
    category: "infrastructure",
    auth: "keyless",
    source: {
      name: "TeleGeography Submarine Cable Map",
      url: "https://www.submarinecablemap.com",
      license: "CC BY-NC-SA 3.0",
      commercialUse: false,
      attribution:
        'Submarine cables: <a href="https://www.submarinecablemap.com">TeleGeography</a> (CC BY-NC-SA 3.0)',
    },
    defaultOpacity: 0.85,
    loadData: async () => {
      const response = await fetch(`${API_URL}/api/v1/infrastructure/submarine-cables`);
      if (!response.ok) throw new Error(`Submarine cables ${response.status}`);
      return (await response.json()) as GeoJSON.FeatureCollection;
    },
    styleLayers: (sourceId) => [
      {
        id: `${sourceId}-lines`,
        type: "line",
        source: sourceId,
        filter: ["==", ["get", "kind"], "cable"],
        paint: {
          "line-color": ["coalesce", ["get", "color"], "#94a3b8"],
          "line-width": ["interpolate", ["linear"], ["zoom"], 1, 0.8, 8, 2.5],
          "line-opacity": 0.85,
        },
      } as LayerSpecification,
      {
        id: `${sourceId}-landings`,
        type: "circle",
        source: sourceId,
        filter: ["==", ["get", "kind"], "landing"],
        minzoom: 3,
        paint: {
          "circle-color": "#e2e8f0",
          "circle-radius": ["interpolate", ["linear"], ["zoom"], 3, 1.5, 8, 4],
          "circle-stroke-color": "#0f172a",
          "circle-stroke-width": 1,
        },
      } as LayerSpecification,
      {
        id: `${sourceId}-labels`,
        type: "symbol",
        source: sourceId,
        filter: ["==", ["get", "kind"], "cable"],
        minzoom: 4,
        layout: {
          "symbol-placement": "line",
          "text-field": ["get", "name"],
          "text-font": LABEL_FONT,
          "text-size": 10,
        },
        paint: { "text-color": "#cbd5e1", "text-halo-color": "#0f172a", "text-halo-width": 1.2 },
      } as LayerSpecification,
    ],
  },
  {
    id: "hospitals",
    kind: "style",
    category: "infrastructure",
    auth: "keyless",
    source: {
      name: "OpenStreetMap (via OpenFreeMap)",
      url: "https://www.openstreetmap.org/copyright",
      license: "ODbL",
      commercialUse: true,
      attribution: "© OpenStreetMap contributors",
    },
    defaultOpacity: 1,
    // Hospital POIs are already in the basemap's vector tiles. OpenMapTiles
    // only includes them from zoom 14 (zoom 13 tiles carry ~200 top POIs).
    basemapSource: "openmaptiles",
    styleLayers: (sourceId) => [
      {
        id: "hospitals-points",
        type: "circle",
        source: sourceId,
        "source-layer": "poi",
        minzoom: 14,
        filter: ["==", ["get", "class"], "hospital"],
        paint: {
          "circle-color": "#ef4444",
          "circle-radius": 5,
          "circle-stroke-color": "#ffffff",
          "circle-stroke-width": 1.5,
        },
      } as LayerSpecification,
      {
        id: "hospitals-labels",
        type: "symbol",
        source: sourceId,
        "source-layer": "poi",
        filter: ["==", ["get", "class"], "hospital"],
        minzoom: 15,
        layout: {
          "text-field": ["coalesce", ["get", "name"], ""],
          "text-font": LABEL_FONT,
          "text-size": 11,
          "text-offset": [0, 1],
          "text-anchor": "top",
        },
        paint: { "text-color": "#fecaca", "text-halo-color": "#111827", "text-halo-width": 1.2 },
      } as LayerSpecification,
    ],
  },
];
