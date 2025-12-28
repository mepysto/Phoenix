"use client";

import Link from "next/link";
import {
  ArrowLeft,
  Palette,
  Map,
  RefreshCw,
  RotateCcw,
  Languages,
} from "lucide-react";
import { Header } from "@/components/layout/Header";
import {
  useSettingsStore,
  LANGUAGE_LABELS,
  THEME_LABELS,
  type Language,
  type Theme,
  type DefaultBasemap,
  type DefaultProjection,
} from "@/store/settingsStore";
import { useTranslation } from "@/lib/i18n/useTranslation";

interface SettingsSectionProps {
  title: string;
  description: string;
  icon: React.ReactNode;
  children: React.ReactNode;
}

function SettingsSection({
  title,
  description,
  icon,
  children,
}: SettingsSectionProps) {
  return (
    <div className="rounded-lg border border-gray-800 bg-gray-900 p-6">
      <div className="mb-4 flex items-start gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary-600/20">
          {icon}
        </div>
        <div>
          <h3 className="font-semibold text-white">{title}</h3>
          <p className="text-sm text-gray-400">{description}</p>
        </div>
      </div>
      <div className="space-y-4">{children}</div>
    </div>
  );
}

interface SelectOptionProps {
  label: string;
  value: string;
  options: { value: string; label: string }[];
  onChange: (value: string) => void;
}

function SelectOption({ label, value, options, onChange }: SelectOptionProps) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-sm text-gray-300">{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="rounded-lg border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-white focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
      >
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    </div>
  );
}

interface ToggleOptionProps {
  label: string;
  description?: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
}

function ToggleOption({
  label,
  description,
  checked,
  onChange,
}: ToggleOptionProps) {
  return (
    <div className="flex items-center justify-between">
      <div>
        <span className="text-sm text-gray-300">{label}</span>
        {description && <p className="text-xs text-gray-500">{description}</p>}
      </div>
      <button
        onClick={() => onChange(!checked)}
        className={`relative h-6 w-11 rounded-full transition-colors ${
          checked ? "bg-primary-600" : "bg-gray-700"
        }`}
      >
        <span
          className={`absolute left-0.5 top-0.5 h-5 w-5 rounded-full bg-white transition-transform ${
            checked ? "translate-x-5" : "translate-x-0"
          }`}
        />
      </button>
    </div>
  );
}

export default function SettingsPage() {
  const { t } = useTranslation();
  const {
    language,
    theme,
    defaultBasemap,
    defaultProjection,
    autoRefresh,
    refreshInterval,
    showClusterMarkers,
    animationsEnabled,
    setLanguage,
    setTheme,
    setDefaultBasemap,
    setDefaultProjection,
    setAutoRefresh,
    setRefreshInterval,
    setShowClusterMarkers,
    setAnimationsEnabled,
    resetToDefaults,
  } = useSettingsStore();

  const languageOptions = Object.entries(LANGUAGE_LABELS).map(
    ([value, label]) => ({
      value,
      label,
    }),
  );

  const themeOptions = Object.entries(THEME_LABELS).map(([value, label]) => ({
    value,
    label,
  }));

  const basemapOptions = [
    { value: "dark", label: t.map.dark },
    { value: "satellite", label: t.map.satellite },
  ];

  const projectionOptions = [
    { value: "globe", label: t.map.globe3d },
    { value: "mercator", label: t.map.view2d },
  ];

  const refreshIntervalOptions = [
    { value: "1", label: "1 min" },
    { value: "5", label: "5 min" },
    { value: "15", label: "15 min" },
    { value: "30", label: "30 min" },
    { value: "60", label: "1 hour" },
  ];

  return (
    <div className="flex min-h-screen flex-col bg-gray-950">
      <Header />

      <main className="flex-1 px-4 py-8 md:px-6 lg:px-8">
        <div className="mx-auto max-w-2xl">
          <Link
            href="/"
            className="mb-6 inline-flex items-center gap-2 text-sm text-gray-400 hover:text-white transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
            {t.common.backToMap}
          </Link>

          <div className="mb-8">
            <h1 className="text-2xl font-bold text-white">
              {t.settings.title}
            </h1>
            <p className="mt-1 text-gray-400">{t.settings.subtitle}</p>
          </div>

          <div className="space-y-6">
            <SettingsSection
              title={t.settings.language}
              description={t.settings.languageDesc}
              icon={<Languages className="h-5 w-5 text-primary-500" />}
            >
              <SelectOption
                label={t.settings.displayLanguage}
                value={language}
                options={languageOptions}
                onChange={(v) => setLanguage(v as Language)}
              />
            </SettingsSection>

            <SettingsSection
              title={t.settings.appearance}
              description={t.settings.appearanceDesc}
              icon={<Palette className="h-5 w-5 text-primary-500" />}
            >
              <SelectOption
                label={t.settings.theme}
                value={theme}
                options={themeOptions}
                onChange={(v) => setTheme(v as Theme)}
              />
              <ToggleOption
                label={t.settings.enableAnimations}
                description={t.settings.animationsDesc}
                checked={animationsEnabled}
                onChange={setAnimationsEnabled}
              />
            </SettingsSection>

            <SettingsSection
              title={t.settings.mapPreferences}
              description={t.settings.mapPreferencesDesc}
              icon={<Map className="h-5 w-5 text-primary-500" />}
            >
              <SelectOption
                label={t.settings.defaultBasemap}
                value={defaultBasemap}
                options={basemapOptions}
                onChange={(v) => setDefaultBasemap(v as DefaultBasemap)}
              />
              <SelectOption
                label={t.settings.defaultView}
                value={defaultProjection}
                options={projectionOptions}
                onChange={(v) => setDefaultProjection(v as DefaultProjection)}
              />
              <ToggleOption
                label={t.settings.showClusterMarkers}
                description={t.settings.clusterMarkersDesc}
                checked={showClusterMarkers}
                onChange={setShowClusterMarkers}
              />
            </SettingsSection>

            <SettingsSection
              title={t.settings.dataSync}
              description={t.settings.dataSyncDesc}
              icon={<RefreshCw className="h-5 w-5 text-primary-500" />}
            >
              <ToggleOption
                label={t.settings.autoRefresh}
                description={t.settings.autoRefreshDesc}
                checked={autoRefresh}
                onChange={setAutoRefresh}
              />
              {autoRefresh && (
                <SelectOption
                  label={t.settings.refreshInterval}
                  value={refreshInterval.toString()}
                  options={refreshIntervalOptions}
                  onChange={(v) => setRefreshInterval(parseInt(v, 10))}
                />
              )}
            </SettingsSection>

            <div className="flex justify-end pt-4">
              <button
                onClick={resetToDefaults}
                className="flex items-center gap-2 rounded-lg border border-gray-700 bg-gray-800 px-4 py-2 text-sm font-medium text-gray-300 hover:bg-gray-700 transition-colors"
              >
                <RotateCcw className="h-4 w-4" />
                {t.settings.resetToDefaults}
              </button>
            </div>

            <div className="rounded-lg border border-gray-800 bg-gray-900/50 p-4 text-center text-sm text-gray-500">
              <p className="text-primary-400">{t.settings.changesApplied}</p>
              <p className="mt-1">{t.settings.autoSaved}</p>
              <p className="mt-1">Version 0.12.0 | Phase 1 MVP</p>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
