import type { Language } from "@/store/settingsStore";
import { en } from "./locales/en";
import { ko } from "./locales/ko";
import { es } from "./locales/es";
import { fr } from "./locales/fr";
import { zh } from "./locales/zh";
import { ar } from "./locales/ar";
import { ru } from "./locales/ru";
import type { Translations } from "./types";

export type { Translations } from "./types";

export const translations: Record<Language, Translations> = {
  en,
  ko,
  es,
  fr,
  zh,
  ar,
  ru,
};
