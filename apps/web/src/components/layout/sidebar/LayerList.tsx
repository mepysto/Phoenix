"use client";

import { KeyRound } from "lucide-react";
import type { LayerConfig } from "@phoenix/shared/types";
import { LAYER_DEFINITIONS_BY_ID, type LayerCategory } from "@/lib/layers/registry";
import { useTranslation } from "@/lib/i18n/useTranslation";
import type { Translations } from "@/lib/i18n/types";
import { useMapStore } from "@/store/mapStore";

const TRANSLATION_KEY: Record<string, keyof Translations["sidebar"]> = {
  events: "disasterEvents",
  satellite: "satelliteImagery",
  radar: "radar",
  "clouds-infrared": "cloudsInfrared",
  "night-lights": "nightLights",
  cyclones: "cyclones",
  shakemaps: "shakemaps",
  fires: "fires",
  "power-plants": "powerPlants",
  dams: "dams",
  hospitals: "hospitals",
  "submarine-cables": "submarineCables",
  satellites: "satellites",
  aircraft: "aircraft",
  vessels: "vessels",
  cameras: "cameras",
  launches: "launches",
};

const MIN_ZOOM_WORTH_NOTING = 3;

type Group = "hazards" | "imagery" | "infrastructure" | "live";
const GROUP_OF: Record<LayerCategory, Group> = {
  weather: "hazards",
  hazards: "hazards",
  satellite: "imagery",
  infrastructure: "infrastructure",
  monitoring: "live",
};
const GROUPS: Group[] = ["hazards", "imagery", "infrastructure", "live"];

/** "Aircraft (ADS-B, zoom 5+)" -> "Aircraft": the detail moves to the line below */
export function plainLayerName(label: string): string {
  return label.replace(/\s*[(（].*[)）]\s*$/, "").trim() || label;
}

export function layerGroup(id: string): Group | null {
  if (id === "events") return null;
  if (id === "satellite") return "imagery";
  const category = LAYER_DEFINITIONS_BY_ID.get(id)?.category;
  return category ? GROUP_OF[category] : "hazards";
}

function LayerRow({ layer }: { layer: LayerConfig }) {
  const { t } = useTranslation();
  const zoom = useMapStore((s) => s.viewport?.zoom);
  const toggleLayer = useMapStore((s) => s.toggleLayer);
  const setLayerOpacity = useMapStore((s) => s.setLayerOpacity);
  const key = TRANSLATION_KEY[layer.id];
  const label = (key && t.sidebar[key]) || layer.name;
  const name = plainLayerName(label);
  const definition = LAYER_DEFINITIONS_BY_ID.get(layer.id);
  const needsKey = definition?.auth !== undefined && definition.auth !== "keyless";
  const minZoom = definition && "minZoom" in definition ? definition.minZoom : undefined;
  const hiddenByZoom = layer.visible && minZoom !== undefined && zoom !== undefined && zoom < minZoom;
  const detail = [
    definition?.source.name,
    // Below zoom 3 the layer shows at any reasonable view; not worth a note
    minZoom !== undefined && minZoom >= MIN_ZOOM_WORTH_NOTING
      ? t.ux.visibleFromZoom.replace("{z}", String(minZoom))
      : null,
  ]
    .filter(Boolean)
    .join(" · ");
  const percent = Math.round(layer.opacity * 100);

  return (
    <li className="rounded-lg px-2 py-2 hover:bg-gray-800/60">
      <div className="flex items-start gap-3">
        <div className="min-w-0 flex-1">
          <span className="flex items-center gap-1.5 text-sm text-gray-100">
            {name}
            {needsKey && (
              <span title={t.sidebar.keyRequired}>
                <KeyRound className="h-3.5 w-3.5 text-amber-400" aria-label={t.sidebar.keyRequired} />
              </span>
            )}
          </span>
          {detail && <span className="block text-xs text-gray-400">{detail}</span>}
          {hiddenByZoom && <span className="block text-xs text-amber-300">{t.ux.zoomInToSee}</span>}
        </div>
        <button
          type="button"
          role="switch"
          aria-checked={layer.visible}
          aria-label={name}
          onClick={() => toggleLayer(layer.id)}
          className={`relative mt-0.5 h-5 w-9 shrink-0 rounded-full transition-colors ${
            layer.visible ? "bg-primary-500" : "bg-gray-700"
          }`}
        >
          <span
            aria-hidden="true"
            className={`absolute top-0.5 h-4 w-4 rounded-full bg-white shadow transition-[inset-inline-start] ${
              layer.visible ? "start-[1.125rem]" : "start-0.5"
            }`}
          />
        </button>
      </div>
      {layer.visible && (
        <label className="mt-2 flex items-center gap-2 text-xs text-gray-400">
          <span className="sr-only">
            {name} {t.sidebar.opacity}
          </span>
          <input
            type="range"
            min="0"
            max="100"
            value={percent}
            onChange={(e) => setLayerOpacity(layer.id, Number(e.target.value) / 100)}
            className="h-1.5 flex-1 cursor-pointer accent-primary-500"
          />
          <span className="w-9 text-end tabular-nums">{percent}%</span>
        </label>
      )}
    </li>
  );
}

/** Overlays in four plain groups (UX plan 5.1), with the disaster markers first */
export function LayerList() {
  const { t } = useTranslation();
  const layers = useMapStore((s) => s.layers);
  const title: Record<Group, string> = {
    hazards: t.ux.layerGroupHazards,
    imagery: t.ux.layerGroupImagery,
    infrastructure: t.ux.layerGroupInfrastructure,
    live: t.ux.layerGroupLive,
  };
  const events = layers.find((l) => l.id === "events");

  return (
    <div className="space-y-5">
      {events && (
        <ul>
          <LayerRow layer={events} />
        </ul>
      )}
      {GROUPS.map((group) => {
        const members = layers.filter((l) => layerGroup(l.id) === group);
        if (members.length === 0) return null;
        return (
          <section key={group} aria-labelledby={`layers-${group}`}>
            <h3 id={`layers-${group}`} className="mb-1 px-2 text-sm font-semibold text-gray-200">
              {title[group]}
            </h3>
            <ul>
              {members.map((layer) => (
                <LayerRow key={layer.id} layer={layer} />
              ))}
            </ul>
          </section>
        );
      })}
    </div>
  );
}
