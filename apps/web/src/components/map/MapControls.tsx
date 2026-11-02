"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  Box,
  Check,
  Globe2,
  Link2,
  Map as MapIcon,
  Moon,
  SatelliteDish,
  ScanEye,
  SlidersHorizontal,
} from "lucide-react";
import { EVENT_TYPES } from "@phoenix/shared/constants";
import { useTranslation } from "@/lib/i18n/useTranslation";
import { VIEW_MODES } from "@/lib/map/viewModes";
import { useMapStore } from "@/store/mapStore";
import { currentMapTheme } from "@/lib/map/basemaps";
import { useEventStore } from "@/store/eventStore";
import { SlideOver } from "@/components/connect/SlideOver";
import { FilterPanel } from "@/components/layout/Sidebar";

interface MapControlsProps {
  is3D: boolean;
  onToggleProjection: () => void;
}

/** Square icon button with a visible tooltip on hover and keyboard focus */
function ToolButton({
  label,
  onClick,
  children,
  pressed,
  className = "",
  badge,
  ...rest
}: {
  label: string;
  onClick: () => void;
  children: React.ReactNode;
  pressed?: boolean;
  className?: string;
  badge?: number;
} & Omit<React.ButtonHTMLAttributes<HTMLButtonElement>, "onClick">) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={label}
      aria-pressed={pressed}
      className={`group relative flex h-10 w-10 items-center justify-center text-gray-300 transition-colors hover:bg-gray-800 hover:text-white focus-visible:z-10 ${className}`}
      {...rest}
    >
      {children}
      {badge ? (
        <span className="absolute right-1 top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-primary-500 px-1 text-[10px] font-semibold text-gray-950">
          {badge}
        </span>
      ) : null}
      <span
        role="presentation"
        className="pointer-events-none absolute left-full top-1/2 ml-2 -translate-y-1/2 whitespace-nowrap rounded-md bg-gray-950 px-2 py-1 text-xs font-medium text-gray-100 opacity-0 shadow-panel transition-opacity group-hover:opacity-100 group-focus-visible:opacity-100"
      >
        {label}
      </span>
    </button>
  );
}

/** Top-left map toolbar: projection, basemap, share link, 3D engine, view mode, filters */
export function MapControls({ is3D, onToggleProjection }: MapControlsProps) {
  const { t } = useTranslation();
  const basemap = useMapStore((s) => s.basemap);
  const toggleBasemap = useMapStore((s) => s.toggleBasemap);
  const viewMode = useMapStore((s) => s.viewMode);
  const setViewMode = useMapStore((s) => s.setViewMode);
  const setEngine = useMapStore((s) => s.setEngine);
  const hiddenFilters = useEventStore(
    (s) => EVENT_TYPES.length - s.visibleTypes.size + (4 - s.visibleSeverities.size),
  );

  // The URL already carries camera/basemap/filters (useMapUrlState)
  const [linkCopied, setLinkCopied] = useState(false);
  const copyViewLink = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(window.location.href);
      setLinkCopied(true);
      setTimeout(() => setLinkCopied(false), 2000);
    } catch {
      // Clipboard blocked (insecure context/permissions): the address bar has it
    }
  }, []);

  const [modeOpen, setModeOpen] = useState(false);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const closeFilters = useCallback(() => setFiltersOpen(false), []);
  const modeRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!modeOpen) return;
    const close = (e: Event) => {
      if (e instanceof KeyboardEvent && e.key !== "Escape") return;
      if (e instanceof MouseEvent && modeRef.current?.contains(e.target as Node)) return;
      setModeOpen(false);
    };
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", close);
    return () => {
      document.removeEventListener("mousedown", close);
      document.removeEventListener("keydown", close);
    };
  }, [modeOpen]);

  return (
    <div
      role="toolbar"
      aria-label={t.ux.mapTools}
      aria-orientation="vertical"
      className="absolute left-4 top-4 z-40 flex flex-col"
    >
      <div className="hud-panel flex flex-col divide-y divide-gray-800 overflow-visible rounded-xl [&>*:first-child]:rounded-t-xl lg:[&>*:nth-child(2)]:rounded-t-xl">
        <ToolButton
          label={t.ux.filters}
          onClick={() => setFiltersOpen(true)}
          badge={hiddenFilters}
          className="lg:hidden"
          aria-haspopup="dialog"
        >
          <SlidersHorizontal className="h-[18px] w-[18px]" aria-hidden="true" />
        </ToolButton>
        <ToolButton
          label={is3D ? t.map.view2d : t.map.globe3d}
          onClick={onToggleProjection}
        >
          {is3D ? (
            <MapIcon className="h-[18px] w-[18px]" aria-hidden="true" />
          ) : (
            <Globe2 className="h-[18px] w-[18px]" aria-hidden="true" />
          )}
        </ToolButton>
        <ToolButton
          label={
            basemap === "dark"
              ? t.map.satellite
              : currentMapTheme() === "light"
                ? t.ux.streetMap
                : t.map.dark
          }
          onClick={toggleBasemap}
        >
          {basemap === "dark" ? (
            <SatelliteDish className="h-[18px] w-[18px]" aria-hidden="true" />
          ) : (
            <Moon className="h-[18px] w-[18px]" aria-hidden="true" />
          )}
        </ToolButton>
        <ToolButton
          label={linkCopied ? t.map.linkCopied : t.map.share}
          onClick={copyViewLink}
        >
          {linkCopied ? (
            <Check className="h-[18px] w-[18px] text-primary-400" aria-hidden="true" />
          ) : (
            <Link2 className="h-[18px] w-[18px]" aria-hidden="true" />
          )}
        </ToolButton>
        <ToolButton label={t.map.engine3d} onClick={() => setEngine("cesium")}>
          <Box className="h-[18px] w-[18px]" aria-hidden="true" />
        </ToolButton>
        <div ref={modeRef} className="relative">
          <ToolButton
            label={`${t.ux.viewMode}: ${t.map.viewModes[viewMode]}`}
            onClick={() => setModeOpen((o) => !o)}
            pressed={viewMode !== "normal"}
            aria-haspopup="menu"
            aria-expanded={modeOpen}
            className={`rounded-b-xl ${viewMode !== "normal" ? "text-primary-300" : ""}`}
          >
            <ScanEye className="h-[18px] w-[18px]" aria-hidden="true" />
          </ToolButton>
          {modeOpen && (
            <div
              role="menu"
              aria-label={t.ux.viewMode}
              className="hud-panel absolute left-full top-0 ml-2 w-44 animate-panel-in rounded-xl p-1"
            >
              {VIEW_MODES.map((mode) => (
                <button
                  key={mode}
                  type="button"
                  role="menuitemradio"
                  aria-checked={viewMode === mode}
                  onClick={() => {
                    setViewMode(mode);
                    setModeOpen(false);
                  }}
                  className={`flex w-full items-center justify-between rounded-lg px-3 py-2 text-start text-sm ${
                    viewMode === mode
                      ? "bg-gray-800 text-white"
                      : "text-gray-300 hover:bg-gray-800 hover:text-white"
                  }`}
                >
                  {t.map.viewModes[mode]}
                  {viewMode === mode && (
                    <Check className="h-4 w-4 text-primary-400" aria-hidden="true" />
                  )}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
      <SlideOver
        open={filtersOpen}
        title={t.sidebar.layersAndFilters}
        onClose={closeFilters}
        closeLabel={t.common.close}
        flush
      >
        <FilterPanel />
      </SlideOver>
    </div>
  );
}
