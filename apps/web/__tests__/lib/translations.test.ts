import { describe, expect, it } from "vitest";
import { EVENT_TYPES } from "@phoenix/shared/constants";
import { translations } from "@/lib/i18n/translations";

describe("translations", () => {
  const locales = Object.entries(translations);

  it("every locale names every event type the API can return", () => {
    for (const [lang, t] of locales) {
      for (const type of EVENT_TYPES) {
        expect(t.sidebar[type], `${lang}.sidebar.${type}`).toBeTruthy();
      }
    }
  });

  it("no locale has an empty string", () => {
    for (const [lang, t] of locales) {
      for (const [section, entries] of Object.entries(t)) {
        for (const [key, value] of Object.entries(entries as Record<string, string>)) {
          expect(value.trim(), `${lang}.${section}.${key}`).not.toBe("");
        }
      }
    }
  });
});
