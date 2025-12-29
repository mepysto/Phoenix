"use client";

import { useState } from "react";
import {
  Layers,
  Filter,
  ChevronDown,
  ChevronRight,
  AlertTriangle,
  Droplets,
  Flame,
  Wind,
  Mountain,
  Skull,
  Factory,
  Sun,
  Eye,
  EyeOff,
} from "lucide-react";
import type { EventType, SeverityLevel } from "@phoenix/shared/types";
import { EVENT_TYPE_COLORS, SEVERITY_COLORS } from "@phoenix/shared/constants";
import { useEventStore } from "@/store/eventStore";
import { useMapStore } from "@/store/mapStore";
import { useTranslation } from "@/lib/i18n/useTranslation";

const EVENT_ICONS: Record<EventType, React.ReactNode> = {
  earthquake: <Mountain className="h-4 w-4" />,
  flood: <Droplets className="h-4 w-4" />,
  wildfire: <Flame className="h-4 w-4" />,
  hurricane: <Wind className="h-4 w-4" />,
  tsunami: <Droplets className="h-4 w-4" />,
  volcano: <Mountain className="h-4 w-4" />,
  war: <Skull className="h-4 w-4" />,
  pollution: <Factory className="h-4 w-4" />,
  drought: <Sun className="h-4 w-4" />,
  other: <AlertTriangle className="h-4 w-4" />,
};

interface FilterSectionProps {
  title: string;
  icon: React.ReactNode;
  children: React.ReactNode;
  defaultOpen?: boolean;
}

function FilterSection({
  title,
  icon,
  children,
  defaultOpen = true,
}: FilterSectionProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div className="border-b border-gray-800">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex w-full items-center justify-between px-4 py-3 hover:bg-gray-800/50 transition-colors"
      >
        <div className="flex items-center gap-2 text-sm font-medium text-white">
          {icon}
          {title}
        </div>
        {isOpen ? (
          <ChevronDown className="h-4 w-4 text-gray-400" />
        ) : (
          <ChevronRight className="h-4 w-4 text-gray-400" />
        )}
      </button>
      {isOpen && <div className="px-4 pb-4">{children}</div>}
    </div>
  );
}

const EVENT_TYPES: EventType[] = [
  "earthquake",
  "flood",
  "wildfire",
  "hurricane",
  "tsunami",
  "volcano",
  "war",
  "pollution",
  "drought",
  "other",
];

const SEVERITY_LEVELS: SeverityLevel[] = ["low", "medium", "high", "critical"];

const LAYER_ID_TO_TRANSLATION_KEY: Record<string, string> = {
  events: "disasterEvents",
  satellite: "satelliteImagery",
  buildings: "buildings3d",
  population: "populationDensity",
};

interface LayerItemProps {
  layer: {
    id: string;
    name: string;
    visible: boolean;
    opacity: number;
  };
  translationKey: string;
  onToggle: () => void;
  onOpacityChange: (opacity: number) => void;
  t: Record<string, string>;
}

function LayerItem({
  layer,
  translationKey,
  onToggle,
  onOpacityChange,
  t,
}: LayerItemProps) {
  const opacityPercent = Math.round(layer.opacity * 100);

  return (
    <div className="rounded px-2 py-1.5 hover:bg-gray-800/50">
      <div className="flex items-center gap-3">
        <button
          onClick={onToggle}
          className="flex items-center justify-center text-gray-400 hover:text-white transition-colors"
          aria-label={layer.visible ? "Hide layer" : "Show layer"}
        >
          {layer.visible ? (
            <Eye className="h-4 w-4 text-primary-500" />
          ) : (
            <EyeOff className="h-4 w-4" />
          )}
        </button>
        <span
          className={`flex-1 text-sm ${layer.visible ? "text-gray-300" : "text-gray-500"}`}
        >
          {t[translationKey] || layer.name}
        </span>
        {layer.visible && (
          <span className="text-xs text-gray-500 min-w-[36px] text-right">
            {opacityPercent}%
          </span>
        )}
      </div>

      {layer.visible && (
        <div className="mt-2 ml-7 pr-1">
          <input
            type="range"
            min="0"
            max="100"
            value={opacityPercent}
            onChange={(e) => onOpacityChange(Number(e.target.value) / 100)}
            className="w-full h-1.5 bg-gray-700 rounded-lg appearance-none cursor-pointer
              [&::-webkit-slider-thumb]:appearance-none
              [&::-webkit-slider-thumb]:w-3
              [&::-webkit-slider-thumb]:h-3
              [&::-webkit-slider-thumb]:bg-primary-500
              [&::-webkit-slider-thumb]:rounded-full
              [&::-webkit-slider-thumb]:cursor-pointer
              [&::-webkit-slider-thumb]:transition-transform
              [&::-webkit-slider-thumb]:hover:scale-125
              [&::-moz-range-thumb]:w-3
              [&::-moz-range-thumb]:h-3
              [&::-moz-range-thumb]:bg-primary-500
              [&::-moz-range-thumb]:rounded-full
              [&::-moz-range-thumb]:border-0
              [&::-moz-range-thumb]:cursor-pointer
              [&::-moz-range-track]:bg-gray-700
              [&::-moz-range-track]:rounded-lg"
            aria-label={`${t[translationKey] || layer.name} ${t.opacity || "opacity"}`}
          />
        </div>
      )}
    </div>
  );
}

export function Sidebar() {
  const {
    visibleTypes,
    visibleSeverities,
    toggleEventType,
    toggleSeverity,
    events,
    isLoading,
  } = useEventStore();
  const { layers, toggleLayer, setLayerOpacity } = useMapStore();
  const { t } = useTranslation();

  return (
    <aside className="hidden lg:flex w-72 flex-col border-r border-gray-800 bg-gray-900">
      <div className="flex items-center gap-2 border-b border-gray-800 px-4 py-3">
        <Layers className="h-5 w-5 text-primary-500" />
        <span className="font-semibold text-white">
          {t.sidebar.layersAndFilters}
        </span>
      </div>

      <div className="flex-1 overflow-y-auto">
        <FilterSection
          title={t.sidebar.eventTypes}
          icon={<Filter className="h-4 w-4" />}
        >
          <div className="space-y-1">
            {EVENT_TYPES.map((type) => (
              <label
                key={type}
                className="flex cursor-pointer items-center gap-3 rounded px-2 py-1.5 hover:bg-gray-800/50"
              >
                <input
                  type="checkbox"
                  checked={visibleTypes.has(type)}
                  onChange={() => toggleEventType(type)}
                  className="h-4 w-4 rounded border-gray-600 bg-gray-700 text-primary-500 focus:ring-primary-500"
                />
                <span style={{ color: EVENT_TYPE_COLORS[type] }}>
                  {EVENT_ICONS[type]}
                </span>
                <span className="text-sm text-gray-300">{t.sidebar[type]}</span>
              </label>
            ))}
          </div>
        </FilterSection>

        <FilterSection
          title={t.sidebar.severity}
          icon={<AlertTriangle className="h-4 w-4" />}
        >
          <div className="space-y-1">
            {SEVERITY_LEVELS.map((severity) => (
              <label
                key={severity}
                className="flex cursor-pointer items-center gap-3 rounded px-2 py-1.5 hover:bg-gray-800/50"
              >
                <input
                  type="checkbox"
                  checked={visibleSeverities.has(severity)}
                  onChange={() => toggleSeverity(severity)}
                  className="h-4 w-4 rounded border-gray-600 bg-gray-700 text-primary-500 focus:ring-primary-500"
                />
                <span
                  className="h-3 w-3 rounded-full"
                  style={{ backgroundColor: SEVERITY_COLORS[severity] }}
                />
                <span className="text-sm text-gray-300">
                  {t.sidebar[severity]}
                </span>
              </label>
            ))}
          </div>
        </FilterSection>

        <FilterSection
          title={t.sidebar.layers}
          icon={<Layers className="h-4 w-4" />}
        >
          <div className="space-y-1">
            {layers.map((layer) => (
              <LayerItem
                key={layer.id}
                layer={layer}
                translationKey={
                  LAYER_ID_TO_TRANSLATION_KEY[layer.id] || layer.id
                }
                onToggle={() => toggleLayer(layer.id)}
                onOpacityChange={(opacity) =>
                  setLayerOpacity(layer.id, opacity)
                }
                t={t.sidebar}
              />
            ))}
          </div>
        </FilterSection>
      </div>

      <div className="border-t border-gray-800 px-4 py-3">
        <div className="flex items-center justify-between text-xs text-gray-500">
          <span>{t.sidebar.dataSource}</span>
          <span className="text-gray-400">
            {isLoading
              ? t.common.loading
              : `${events.length} ${t.sidebar.eventsCount}`}
          </span>
        </div>
      </div>
    </aside>
  );
}
