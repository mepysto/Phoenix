import { eventsAPI, type AgentChatBody, type ApiDisasterEvent, type ApiMapAction } from "@/lib/api/client";
import { briefFromEvent, type BriefCaptions } from "@/lib/brief";
import { LAYER_DEFINITIONS } from "@/lib/layers/registry";
import { useBriefStore } from "@/store/briefStore";
import { ALL_EVENT_TYPES, ALL_SEVERITIES, useEventStore } from "@/store/eventStore";
import { useMapStore } from "@/store/mapStore";
import { useTimelineStore } from "@/store/timelineStore";

const OVERLAY_IDS = LAYER_DEFINITIONS.map((definition) => definition.id);

/** What the user is looking at, sent with every message so answers are grounded */
export function buildMapContext(): AgentChatBody["context"] {
  const { viewport, layers } = useMapStore.getState();
  const { visibleTypes, visibleSeverities, selectedEvent } = useEventStore.getState();
  const at = useTimelineStore.getState().at;
  const overlays = new Set(OVERLAY_IDS);
  return {
    bbox: viewport?.bbox,
    center_lat: viewport?.center.lat,
    center_lng: viewport?.center.lng,
    zoom: viewport?.zoom,
    at,
    visible_layers: layers.filter((l) => l.visible && overlays.has(l.id)).map((l) => l.id),
    available_layers: OVERLAY_IDS,
    types: visibleTypes.size < ALL_EVENT_TYPES.length ? [...visibleTypes] : null,
    severities: visibleSeverities.size < ALL_SEVERITIES.length ? [...visibleSeverities] : null,
    selected_event_id: selectedEvent?.id ?? null,
  };
}

export interface ActionDeps {
  /** Opens an event's card and flies to it */
  focusEvent: (event: ApiDisasterEvent) => void;
  captions: BriefCaptions;
}

/**
 * Apply the assistant's map actions (already validated by the API). Returns
 * how many were applied; an event that cannot be loaded is skipped.
 */
export async function applyMapActions(actions: ApiMapAction[], deps: ActionDeps): Promise<number> {
  let applied = 0;
  for (const action of actions) {
    switch (action.type) {
      case "fly_to":
        useMapStore.getState().requestCamera({ lng: action.lng, lat: action.lat, zoom: action.zoom ?? 5, bearing: 0, pitch: 0 });
        break;
      case "set_layers":
        useMapStore.getState().setOverlaysVisible(action.show ?? [], action.hide ?? []);
        break;
      case "set_event_filters":
        useEventStore.getState().setVisibility(action.types ?? undefined, action.severities ?? undefined);
        break;
      case "set_time":
        useTimelineStore.getState().setAt(action.at ?? null);
        break;
      case "select_event":
      case "play_brief": {
        let event: ApiDisasterEvent;
        try {
          event = await eventsAPI.get(action.eventId);
        } catch {
          continue;
        }
        if (action.type === "select_event") {
          deps.focusEvent(event);
        } else {
          const brief = briefFromEvent(event, deps.captions);
          if (!brief) continue;
          useBriefStore.getState().start(brief);
        }
        break;
      }
      default:
        continue;
    }
    applied += 1;
  }
  return applied;
}
