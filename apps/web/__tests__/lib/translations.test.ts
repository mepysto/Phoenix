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
    // Sections may nest (e.g. brief.captions)
    const check = (path: string, value: unknown) => {
      if (typeof value === "string") expect(value.trim(), path).not.toBe("");
      else for (const [key, inner] of Object.entries(value as object)) check(`${path}.${key}`, inner);
    };
    for (const [lang, t] of locales) check(lang, t);
  });
});
