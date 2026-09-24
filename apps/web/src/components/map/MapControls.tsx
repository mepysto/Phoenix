"use client";

import { useCallback, useState } from "react";
import { useTranslation } from "@/lib/i18n/useTranslation";
import { VIEW_MODES, isViewMode } from "@/lib/map/viewModes";
import { useMapStore } from "@/store/mapStore";

interface MapControlsProps {
  is3D: boolean;
  onToggleProjection: () => void;
}

/** Top-left map controls: projection, basemap, share link, 3D engine, view mode */
export function MapControls({ is3D, onToggleProjection }: MapControlsProps) {
  const { t } = useTranslation();
  const basemap = useMapStore((s) => s.basemap);
  const toggleBasemap = useMapStore((s) => s.toggleBasemap);
  const viewMode = useMapStore((s) => s.viewMode);
  const setViewMode = useMapStore((s) => s.setViewMode);
  const setEngine = useMapStore((s) => s.setEngine);

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

  return (
    <div className="absolute left-4 top-4 flex flex-col gap-2">
      <button
        onClick={onToggleProjection}
        className="rounded-lg bg-gray-900/90 px-3 py-2 text-sm font-medium text-white shadow-lg backdrop-blur hover:bg-gray-800 transition-colors"
      >
        {is3D ? t.map.view2d : t.map.globe3d}
      </button>
      <button
        onClick={toggleBasemap}
        className="rounded-lg bg-gray-900/90 px-3 py-2 text-sm font-medium text-white shadow-lg backdrop-blur hover:bg-gray-800 transition-colors"
      >
        {basemap === "dark" ? t.map.satellite : t.map.dark}
      </button>
      <button
        onClick={copyViewLink}
        className="rounded-lg bg-gray-900/90 px-3 py-2 text-sm font-medium text-white shadow-lg backdrop-blur hover:bg-gray-800 transition-colors"
      >
        <span aria-live="polite">{linkCopied ? t.map.linkCopied : t.map.share}</span>
      </button>
      <button
        onClick={() => setEngine("cesium")}
        className="rounded-lg bg-gray-900/90 px-3 py-2 text-sm font-medium text-white shadow-lg backdrop-blur hover:bg-gray-800 transition-colors"
      >
        {t.map.engine3d}
      </button>
      <label className="sr-only" htmlFor="view-mode">
        {t.map.viewMode}
      </label>
      <select
        id="view-mode"
        value={viewMode}
        onChange={(e) => isViewMode(e.target.value) && setViewMode(e.target.value)}
        className="rounded-lg bg-gray-900/90 px-3 py-2 text-sm font-medium text-white shadow-lg backdrop-blur hover:bg-gray-800 focus:outline-none focus:ring-1 focus:ring-primary-500"
        title={t.map.viewMode}
      >
        {VIEW_MODES.map((mode) => (
          <option key={mode} value={mode}>
            {t.map.viewModes[mode]}
          </option>
        ))}
      </select>
    </div>
  );
}
