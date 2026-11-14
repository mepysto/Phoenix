"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Box, Check, ChevronDown, Eye, Link2, SlidersHorizontal } from "lucide-react";
import { EVENT_TYPES } from "@phoenix/shared/constants";
import { useTranslation } from "@/lib/i18n/useTranslation";
import { VIEW_MODES } from "@/lib/map/viewModes";
import { useMapStore } from "@/store/mapStore";
import { currentMapTheme } from "@/lib/map/basemaps";
import { useEventStore } from "@/store/eventStore";
import { useUiStore } from "@/store/uiStore";
import { SlideOver } from "@/components/connect/SlideOver";
import { FilterPanel } from "@/components/layout/Sidebar";

interface MapControlsProps {
  is3D: boolean;
  onToggleProjection: () => void;
}

const BUTTON =
  "hud-panel flex h-10 items-center gap-2 rounded-xl px-3 text-sm font-medium text-gray-100 transition-colors hover:bg-gray-800";

function Choice({
  checked,
  onSelect,
  children,
}: {
  checked: boolean;
  onSelect: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      role="menuitemradio"
      aria-checked={checked}
      onClick={onSelect}
      className={`flex w-full items-center justify-between rounded-lg px-3 py-2 text-start text-sm ${
        checked ? "bg-gray-800 text-white" : "text-gray-300 hover:bg-gray-800 hover:text-white"
      }`}
    >
      {children}
      {checked && <Check className="h-4 w-4 text-primary-400" aria-hidden="true" />}
    </button>
  );
}

function MenuGroup({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div role="group" aria-label={label} className="py-1">
      <p className="px-3 pb-1 pt-1.5 text-xs font-semibold text-gray-400">{label}</p>
      {children}
    </div>
  );
}

/**
 * Map tools (UX plan 5.1): named buttons instead of a column of icons.
 * "View" gathers globe/flat, map/satellite, sensor view and the detailed 3D
 * engine; "Share" copies a link to exactly this view.
 */
export function MapControls({ is3D, onToggleProjection }: MapControlsProps) {
  const { t } = useTranslation();
  const basemap = useMapStore((s) => s.basemap);
  const setBasemap = useMapStore((s) => s.setBasemap);
  const viewMode = useMapStore((s) => s.viewMode);
  const setViewMode = useMapStore((s) => s.setViewMode);
  const setEngine = useMapStore((s) => s.setEngine);
  const phoneOverlay = useUiStore((s) => s.phoneOverlay);
  const togglePhoneOverlay = useUiStore((s) => s.togglePhoneOverlay);
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

  const [viewOpen, setViewOpen] = useState(false);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const closeFilters = useCallback(() => setFiltersOpen(false), []);
  const viewRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!viewOpen) return;
    const close = (e: Event) => {
      if (e instanceof KeyboardEvent && e.key !== "Escape") return;
      if (e instanceof MouseEvent && viewRef.current?.contains(e.target as Node)) return;
      setViewOpen(false);
    };
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", close);
    return () => {
      document.removeEventListener("mousedown", close);
      document.removeEventListener("keydown", close);
    };
  }, [viewOpen]);

  const mapLabel = currentMapTheme() === "light" ? t.ux.streetMap : t.map.dark;

  return (
    <div role="toolbar" aria-label={t.ux.mapTools} className="absolute left-4 top-4 z-40 flex items-start gap-2">
      <button
        type="button"
        onClick={() => setFiltersOpen(true)}
        aria-haspopup="dialog"
        className={`${BUTTON} lg:hidden`}
      >
        <SlidersHorizontal className="h-4 w-4" aria-hidden="true" />
        {t.ux.filters}
        {hiddenFilters > 0 && (
          <span className="flex h-5 min-w-5 items-center justify-center rounded-full bg-primary-500 px-1 text-xs font-semibold text-gray-950">
            {hiddenFilters}
          </span>
        )}
      </button>

      <div ref={viewRef} className="relative">
        <button
          type="button"
          onClick={() => setViewOpen((o) => !o)}
          aria-haspopup="menu"
          aria-expanded={viewOpen}
          className={`${BUTTON} ${viewMode !== "normal" ? "text-primary-200" : ""}`}
        >
          <Eye className="h-4 w-4" aria-hidden="true" />
          {t.ux.mapView}
          <ChevronDown className="h-3.5 w-3.5 text-gray-400" aria-hidden="true" />
        </button>
        {viewOpen && (
          <div
            role="menu"
            aria-label={t.ux.mapView}
            // A choice closes the menu, like any menu
            onClick={(e) => {
              if ((e.target as HTMLElement).closest('[role^="menuitem"]')) setViewOpen(false);
            }}
            className="hud-panel absolute left-0 top-full mt-2 w-56 animate-panel-in divide-y divide-gray-800 rounded-xl p-1"
          >
            <MenuGroup label={`${t.map.globe3d} / ${t.map.view2d}`}>
              <Choice checked={is3D} onSelect={() => !is3D && onToggleProjection()}>
                {t.map.globe3d}
              </Choice>
              <Choice checked={!is3D} onSelect={() => is3D && onToggleProjection()}>
                {t.map.view2d}
              </Choice>
            </MenuGroup>
            <MenuGroup label={`${mapLabel} / ${t.map.satellite}`}>
              <Choice checked={basemap !== "satellite"} onSelect={() => setBasemap("dark")}>
                {mapLabel}
              </Choice>
              <Choice checked={basemap === "satellite"} onSelect={() => setBasemap("satellite")}>
                {t.map.satellite}
              </Choice>
            </MenuGroup>
            <MenuGroup label={t.ux.viewMode}>
              {VIEW_MODES.map((mode) => (
                <Choice key={mode} checked={viewMode === mode} onSelect={() => setViewMode(mode)}>
                  {t.map.viewModes[mode]}
                </Choice>
              ))}
            </MenuGroup>
            {/* Phones keep the map clear: the timeline and legend open from here */}
            <div className="py-1 lg:hidden">
              <button
                type="button"
                role="menuitemcheckbox"
                aria-checked={phoneOverlay === "timeline"}
                onClick={() => togglePhoneOverlay("timeline")}
                className="flex w-full items-center justify-between rounded-lg px-3 py-2 text-start text-sm text-gray-300 hover:bg-gray-800 hover:text-white"
              >
                {t.ux.timelineMenu}
                {phoneOverlay === "timeline" && <Check className="h-4 w-4 text-primary-400" aria-hidden="true" />}
              </button>
              <button
                type="button"
                role="menuitemcheckbox"
                aria-checked={phoneOverlay === "legend"}
                onClick={() => togglePhoneOverlay("legend")}
                className="flex w-full items-center justify-between rounded-lg px-3 py-2 text-start text-sm text-gray-300 hover:bg-gray-800 hover:text-white"
              >
                {t.ux.legend}
                {phoneOverlay === "legend" && <Check className="h-4 w-4 text-primary-400" aria-hidden="true" />}
              </button>
            </div>
            <div className="py-1">
              {/* Phones keep only Filters and View on the map; sharing moves here */}
              <button
                type="button"
                role="menuitem"
                onClick={copyViewLink}
                className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-start text-sm text-gray-300 hover:bg-gray-800 hover:text-white lg:hidden"
              >
                <Link2 className="h-4 w-4" aria-hidden="true" />
                {t.map.share}
              </button>
              <button
                type="button"
                role="menuitem"
                onClick={() => setEngine("cesium")}
                className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-start text-sm text-gray-300 hover:bg-gray-800 hover:text-white"
              >
                <Box className="h-4 w-4" aria-hidden="true" />
                {t.map.engine3d}
              </button>
            </div>
          </div>
        )}
      </div>

      <button type="button" onClick={copyViewLink} className={`${BUTTON} hidden lg:flex`} aria-live="polite">
        {linkCopied ? (
          <Check className="h-4 w-4 text-primary-400" aria-hidden="true" />
        ) : (
          <Link2 className="h-4 w-4" aria-hidden="true" />
        )}
        {linkCopied ? t.map.linkCopied : t.map.share}
      </button>

      <SlideOver
        open={filtersOpen}
        title={t.sidebar.layersAndFilters}
        onClose={closeFilters}
        closeLabel={t.common.close}
        flush
      >
        <FilterPanel showSummary={false} />
      </SlideOver>
    </div>
  );
}
