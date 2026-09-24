import { act, render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { SettingsProvider } from "@/components/providers/SettingsProvider";
import { useSettingsStore } from "@/store/settingsStore";

describe("SettingsProvider language sync", () => {
  it("sets <html lang> and switches to RTL for Arabic", () => {
    render(<SettingsProvider>x</SettingsProvider>);

    act(() => useSettingsStore.getState().setLanguage("ar"));
    expect(document.documentElement.lang).toBe("ar");
    expect(document.documentElement.dir).toBe("rtl");

    act(() => useSettingsStore.getState().setLanguage("ko"));
    expect(document.documentElement.lang).toBe("ko");
    expect(document.documentElement.dir).toBe("ltr");
  });
});
