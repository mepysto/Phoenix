"use client";

import { useEffect } from "react";
import { useSettingsStore } from "@/store/settingsStore";

export function SettingsProvider({ children }: { children: React.ReactNode }) {
  const { theme, animationsEnabled } = useSettingsStore();

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
