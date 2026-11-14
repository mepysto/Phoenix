"use client";

import { useState } from "react";
import { Filter, Layers } from "lucide-react";
import { ViewSummary } from "@/components/map/ViewSummary";
import { useTranslation } from "@/lib/i18n/useTranslation";
import { useUiStore } from "@/store/uiStore";
import { DisasterFilters } from "./sidebar/DisasterFilters";
import { LayerList } from "./sidebar/LayerList";

type Tab = "disasters" | "layers";

/**
 * Map filters in two tabs (UX plan 5.1): what disasters to show, and which
 * overlays to draw. Shared by the desktop panel and the phone drawer.
 */
export function FilterPanel({ showSummary = true }: { showSummary?: boolean }) {
  const { t } = useTranslation();
  const setFocusEvent = useUiStore((s) => s.setFocusEvent);
  const [tab, setTab] = useState<Tab>("disasters");
  const tabs: { id: Tab; label: string; icon: typeof Filter }[] = [
    { id: "disasters", label: t.ux.navDisasters, icon: Filter },
    { id: "layers", label: t.sidebar.layers, icon: Layers },
  ];

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div role="tablist" aria-label={t.sidebar.layersAndFilters} className="flex border-b border-gray-800 px-2">
        {tabs.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            id={`filter-tab-${id}`}
            type="button"
            role="tab"
            aria-selected={tab === id}
            aria-controls={`filter-panel-${id}`}
            onClick={() => setTab(id)}
            className={`flex flex-1 items-center justify-center gap-2 border-b-2 px-3 py-3 text-sm font-medium transition-colors ${
              tab === id ? "border-primary-400 text-white" : "border-transparent text-gray-400 hover:text-white"
            }`}
          >
            <Icon className="h-4 w-4" aria-hidden="true" />
            {label}
          </button>
        ))}
      </div>
      <div
        id={`filter-panel-${tab}`}
        role="tabpanel"
        aria-labelledby={`filter-tab-${tab}`}
        className="flex-1 space-y-5 overflow-y-auto p-3"
      >
        {tab === "disasters" ? (
          <>
            {showSummary && <ViewSummary variant="panel" onSelect={setFocusEvent} />}
            <DisasterFilters />
          </>
        ) : (
          <LayerList />
        )}
      </div>
    </div>
  );
}

export function Sidebar() {
  const hidden = useUiStore((s) => s.sidebarHidden || s.opsMode);
  if (hidden) return null;
  return (
    <aside className="hidden w-80 flex-col border-e border-gray-800 bg-gray-900 lg:flex">
      <FilterPanel />
    </aside>
  );
}
