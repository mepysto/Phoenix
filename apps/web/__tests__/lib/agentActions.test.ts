import { beforeEach, describe, expect, it, vi } from "vitest";
import { applyMapActions, buildMapContext } from "@/lib/agent/actions";
import { eventsAPI, type ApiDisasterEvent, type ApiMapAction } from "@/lib/api/client";
import { useBriefStore } from "@/store/briefStore";
import { ALL_EVENT_TYPES, useEventStore } from "@/store/eventStore";
import { useMapStore } from "@/store/mapStore";
import { useTimelineStore } from "@/store/timelineStore";

const CAPTIONS = { before: "b", onset: "o", now: "n", context: "c" };
const EVENT_ID = "0b6f7c2e-7d1a-4c6e-9d57-1f0a3c1b2e4d";
const event = {
  id: EVENT_ID,
  type: "earthquake",
  title: "M 6.2 - Near Tokyo",
  location: { lat: 35.7, lng: 139.7 },
  startDate: "2026-09-23T00:00:00Z",
  endDate: null,
} as unknown as ApiDisasterEvent;

describe("applyMapActions", () => {
  beforeEach(() => {
    useBriefStore.getState().stop();
    useTimelineStore.getState().setAt(null);
    useMapStore.getState().showOnlyOverlays([]);
    vi.restoreAllMocks();
  });

  it("moves the camera, layers, filters and time", async () => {
    const actions = [
      { type: "fly_to", lat: 35.7, lng: 139.7, zoom: 6 },
      { type: "set_layers", show: ["shakemaps"], hide: [] },
      { type: "set_event_filters", types: ["earthquake"], severities: null },
      { type: "set_time", at: "2026-09-20T00:00:00Z" },
    ] as ApiMapAction[];
    const applied = await applyMapActions(actions, { focusEvent: vi.fn(), captions: CAPTIONS });

    expect(applied).toBe(4);
    expect(useMapStore.getState().cameraRequest?.view).toMatchObject({ lat: 35.7, lng: 139.7, zoom: 6 });
    expect(useMapStore.getState().layers.find((l) => l.id === "shakemaps")?.visible).toBe(true);
    expect([...useEventStore.getState().visibleTypes]).toEqual(["earthquake"]);
    expect(useTimelineStore.getState().at).toBe("2026-09-20T00:00:00Z");
  });

  it("opens an event and plays its brief", async () => {
    vi.spyOn(eventsAPI, "get").mockResolvedValue(event as Awaited<ReturnType<typeof eventsAPI.get>>);
    const focusEvent = vi.fn();
    const applied = await applyMapActions(
      [
        { type: "select_event", eventId: EVENT_ID },
        { type: "play_brief", eventId: EVENT_ID },
      ] as ApiMapAction[],
      { focusEvent, captions: CAPTIONS },
    );
    expect(applied).toBe(2);
    expect(focusEvent).toHaveBeenCalledWith(event);
    expect(useBriefStore.getState().brief?.eventId).toBe(EVENT_ID);
  });

  it("skips an event that cannot be loaded", async () => {
    vi.spyOn(eventsAPI, "get").mockRejectedValue(new Error("404"));
    const focusEvent = vi.fn();
    const applied = await applyMapActions([{ type: "select_event", eventId: EVENT_ID }] as ApiMapAction[], {
      focusEvent,
      captions: CAPTIONS,
    });
    expect(applied).toBe(0);
    expect(focusEvent).not.toHaveBeenCalled();
  });
});

describe("buildMapContext", () => {
  it("describes the visible map", () => {
    useEventStore.getState().setVisibility(ALL_EVENT_TYPES, undefined);
    useMapStore.getState().setViewport({ bbox: [120, 20, 150, 50], zoom: 4, center: { lat: 35, lng: 135 } });
    useMapStore.getState().showOnlyOverlays(["fires"]);
    useTimelineStore.getState().setAt("2026-09-20T00:00:00.000Z");

    const context = buildMapContext();
    expect(context).toMatchObject({
      bbox: [120, 20, 150, 50],
      center_lat: 35,
      zoom: 4,
      at: "2026-09-20T00:00:00.000Z",
      visible_layers: ["fires"],
      types: null, // all types: not sent as a filter
    });
    expect(context?.available_layers).toContain("shakemaps");
  });
});
