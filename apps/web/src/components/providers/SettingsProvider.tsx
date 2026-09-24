"use client";

import { useEffect } from "react";
import { useSettingsStore } from "@/store/settingsStore";

const RTL_LANGUAGES = new Set(["ar"]);

export function SettingsProvider({ children }: { children: React.ReactNode }) {
  const { theme, animationsEnabled, language } = useSettingsStore();

  // Screen readers, hyphenation and fonts follow <html lang>; Arabic needs RTL.
  // The language lives in client storage, so the server renders "en" and this
  // syncs it after hydration.
  useEffect(() => {
    const root = document.documentElement;
    root.lang = language;
    root.dir = RTL_LANGUAGES.has(language) ? "rtl" : "ltr";
  }, [language]);

  useEffect(() => {
    const root = document.documentElement;

    if (theme === "system") {
      const prefersDark = window.matchMedia(
        "(prefers-color-scheme: dark)",
      ).matches;
      root.classList.toggle("dark", prefersDark);
      root.classList.toggle("light", !prefersDark);
    } else {
      root.classList.remove("dark", "light");
      root.classList.add(theme);
    }
  }, [theme]);

  useEffect(() => {
    const root = document.documentElement;
    root.classList.toggle("no-animations", !animationsEnabled);
  }, [animationsEnabled]);

  return <>{children}</>;
}
