import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { useKeyboardShortcuts } from "@/hooks/useKeyboardShortcuts";
import { useMapStore } from "@/store/mapStore";
import { useUiStore } from "@/store/uiStore";

const press = (key: string, target: EventTarget = window, init: KeyboardEventInit = {}) =>
  act(() => {
    target.dispatchEvent(new KeyboardEvent("keydown", { key, bubbles: true, ...init }));
  });

describe("useKeyboardShortcuts", () => {
  beforeEach(() => {
    useUiStore.setState({ opsMode: false, sidebarHidden: false, shortcutsOpen: false, follow: null });
    useMapStore.getState().setViewMode("normal");
    useMapStore.getState().setBasemap("dark");
    useMapStore.getState().setInspected(null);
  });

  it("toggles ops mode, the sidebar and the help", () => {
    renderHook(() => useKeyboardShortcuts());
    press("o");
    press("L");
    press("?");
    expect(useUiStore.getState()).toMatchObject({ opsMode: true, sidebarHidden: true, shortcutsOpen: true });
    press("Escape");
    expect(useUiStore.getState().shortcutsOpen).toBe(false);
  });

  it("switches basemap and cycles view modes", () => {
    renderHook(() => useKeyboardShortcuts());
    press("2");
    press("v");
    press("v");
    expect(useMapStore.getState().basemap).toBe("satellite");
    expect(useMapStore.getState().viewMode).toBe("flir");
  });

  it("Escape closes the inspected card and stops following", () => {
    renderHook(() => useKeyboardShortcuts());
    useMapStore.getState().setInspected({ layerId: "aircraft", properties: {}, lng: 0, lat: 0 });
    useUiStore.getState().setFollow({ layerId: "aircraft", key: "hex", value: "abc" });
    press("Escape");
    expect(useMapStore.getState().inspected).toBeNull();
    expect(useUiStore.getState().follow).toBeNull();
  });

  it("ignores typing in fields and modified keys", () => {
    renderHook(() => useKeyboardShortcuts());
    const input = document.createElement("input");
    document.body.appendChild(input);
    press("o", input);
    press("o", window, { ctrlKey: true });
    expect(useUiStore.getState().opsMode).toBe(false);
    input.remove();
  });
});
