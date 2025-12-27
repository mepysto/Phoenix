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
} from "lucide-react";
import type { EventType, SeverityLevel } from "@phoenix/shared/types";
import {
  EVENT_TYPE_LABELS,
  EVENT_TYPE_COLORS,
  SEVERITY_LABELS,
  SEVERITY_COLORS,
} from "@phoenix/shared/constants";
import { useEventStore } from "@/store/eventStore";

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

export function Sidebar() {
  const { filter, toggleEventType, toggleSeverity, events, isLoading } = useEventStore();
  
  const selectedTypes = new Set(filter.types || []);
  const selectedSeverities = new Set(filter.severities || []);

  const eventTypes = Object.keys(EVENT_TYPE_LABELS) as EventType[];
  const severityLevels = Object.keys(SEVERITY_LABELS) as SeverityLevel[];

  return (
    <aside className="hidden lg:flex w-72 flex-col border-r border-gray-800 bg-gray-900">
      <div className="flex items-center gap-2 border-b border-gray-800 px-4 py-3">
        <Layers className="h-5 w-5 text-primary-500" />
        <span className="font-semibold text-white">Layers & Filters</span>
      </div>

      <div className="flex-1 overflow-y-auto">
        <FilterSection
          title="Event Types"
          icon={<Filter className="h-4 w-4" />}
        >
          <div className="space-y-1">
            {eventTypes.map((type) => (
              <label
                key={type}
                className="flex cursor-pointer items-center gap-3 rounded px-2 py-1.5 hover:bg-gray-800/50"
              >
                <input
                  type="checkbox"
                  checked={selectedTypes.has(type)}
                  onChange={() => toggleEventType(type)}
                  className="h-4 w-4 rounded border-gray-600 bg-gray-700 text-primary-500 focus:ring-primary-500"
                />
                <span style={{ color: EVENT_TYPE_COLORS[type] }}>
                  {EVENT_ICONS[type]}
                </span>
                <span className="text-sm text-gray-300">
                  {EVENT_TYPE_LABELS[type]}
                </span>
              </label>
            ))}
          </div>
        </FilterSection>

        <FilterSection
          title="Severity"
          icon={<AlertTriangle className="h-4 w-4" />}
        >
          <div className="space-y-1">
            {severityLevels.map((severity) => (
              <label
                key={severity}
                className="flex cursor-pointer items-center gap-3 rounded px-2 py-1.5 hover:bg-gray-800/50"
              >
                <input
                  type="checkbox"
                  checked={selectedSeverities.has(severity)}
                  onChange={() => toggleSeverity(severity)}
                  className="h-4 w-4 rounded border-gray-600 bg-gray-700 text-primary-500 focus:ring-primary-500"
                />
                <span
                  className="h-3 w-3 rounded-full"
                  style={{ backgroundColor: SEVERITY_COLORS[severity] }}
                />
                <span className="text-sm text-gray-300">
                  {SEVERITY_LABELS[severity]}
                </span>
              </label>
            ))}
          </div>
        </FilterSection>

        <FilterSection title="Layers" icon={<Layers className="h-4 w-4" />}>
          <div className="space-y-1">
            {["Satellite Imagery", "3D Buildings", "Population Density"].map(
              (layer) => (
                <label
                  key={layer}
                  className="flex cursor-pointer items-center gap-3 rounded px-2 py-1.5 hover:bg-gray-800/50"
                >
                  <input
                    type="checkbox"
                    defaultChecked={layer === "Satellite Imagery"}
                    className="h-4 w-4 rounded border-gray-600 bg-gray-700 text-primary-500 focus:ring-primary-500"
                  />
                  <span className="text-sm text-gray-300">{layer}</span>
                </label>
              )
            )}
          </div>
        </FilterSection>
      </div>

      <div className="border-t border-gray-800 px-4 py-3">
        <div className="flex items-center justify-between text-xs text-gray-500">
          <span>Data: GDACS, Copernicus EMS</span>
          <span className="text-gray-400">
            {isLoading ? "Loading..." : `${events.length} events`}
          </span>
        </div>
      </div>
    </aside>
  );
}
