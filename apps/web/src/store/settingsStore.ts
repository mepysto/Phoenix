import { create, StateCreator } from "zustand";
import { persist, PersistOptions } from "zustand/middleware";

export type Language = "en" | "ko" | "es" | "fr" | "zh" | "ar" | "ru";
export type Theme = "dark" | "light" | "system";
export type DefaultBasemap = "dark" | "satellite";
export type DefaultProjection = "globe" | "mercator";

interface SettingsState {
  language: Language;
  theme: Theme;
  defaultBasemap: DefaultBasemap;
  defaultProjection: DefaultProjection;
  autoRefresh: boolean;
  refreshInterval: number;
  showClusterMarkers: boolean;
  animationsEnabled: boolean;
}

interface SettingsActions {
  setLanguage: (language: Language) => void;
  setTheme: (theme: Theme) => void;
  setDefaultBasemap: (basemap: DefaultBasemap) => void;
  setDefaultProjection: (projection: DefaultProjection) => void;
  setAutoRefresh: (enabled: boolean) => void;
  setRefreshInterval: (minutes: number) => void;
  setShowClusterMarkers: (enabled: boolean) => void;
  setAnimationsEnabled: (enabled: boolean) => void;
  resetToDefaults: () => void;
}

type SettingsStore = SettingsState & SettingsActions;

const defaultSettings: SettingsState = {
  language: "en",
  theme: "dark",
  defaultBasemap: "dark",
  defaultProjection: "globe",
  autoRefresh: true,
  refreshInterval: 5,
  showClusterMarkers: true,
  animationsEnabled: true,
};

const storeImpl: StateCreator<
  SettingsStore,
  [],
  [["zustand/persist", unknown]]
> = (set) => ({
  ...defaultSettings,

  setLanguage: (language) => set({ language }),

  setTheme: (theme) => set({ theme }),

  setDefaultBasemap: (defaultBasemap) => set({ defaultBasemap }),

  setDefaultProjection: (defaultProjection) => set({ defaultProjection }),

  setAutoRefresh: (autoRefresh) => set({ autoRefresh }),

  setRefreshInterval: (refreshInterval) => set({ refreshInterval }),

  setShowClusterMarkers: (showClusterMarkers) => set({ showClusterMarkers }),

  setAnimationsEnabled: (animationsEnabled) => set({ animationsEnabled }),

  resetToDefaults: () => set(defaultSettings),
});

type SettingsPersist = (
  config: StateCreator<SettingsStore, [], [["zustand/persist", unknown]]>,
  options: PersistOptions<SettingsStore>,
) => StateCreator<SettingsStore, [], [["zustand/persist", unknown]]>;

export const useSettingsStore = create<SettingsStore>()(
  (persist as SettingsPersist)(storeImpl, {
    name: "phoenix-settings",
  }),
);

export const LANGUAGE_LABELS: Record<Language, string> = {
  en: "English",
  ko: "한국어",
  es: "Español",
  fr: "Français",
  zh: "中文",
  ar: "العربية",
  ru: "Русский",
};

export const THEME_LABELS: Record<Theme, string> = {
  dark: "Dark",
  light: "Light",
  system: "System",
};
