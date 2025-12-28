"use client";

import { useSettingsStore } from "@/store/settingsStore";
import { translations, type Translations } from "./translations";

export function useTranslation(): { t: Translations; lang: string } {
  const { language } = useSettingsStore();
  return {
    t: translations[language] || translations.en,
    lang: language,
  };
}
