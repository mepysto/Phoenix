"""Tools the map agent can call.

Data tools run here against the database and return compact JSON. Map
tools change the user's map: they are validated here and handed to the web
app, which applies them. A tool the model calls wrongly gets an error result
(so it can correct itself) and is never forwarded.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, TypeAdapter, ValidationError

from src.models.event import EventType, SeverityLevel
from src.schemas.agent import MapAction, MapContext
from src.schemas.event import EventFilter, EventResponse
from src.services.event_service import EventService

MAX_RESULTS = 20
DESCRIPTION_CHARS = 400

_TYPES = [t.value for t in EventType]
_SEVERITIES = [s.value for s in SeverityLevel]
_FILTER_PROPS: dict[str, Any] = {
    "types": {"type": "array", "items": {"type": "string", "enum": _TYPES}},
    "severities": {"type": "array", "items": {"type": "string", "enum": _SEVERITIES}},
    "at": {
        "type": "string",
        "description": "ISO 8601 instant: only events ongoing then. Omit for currently active events.",
    },
}
_BBOX = {
    "type": "array",
    "items": {"type": "number"},
    "minItems": 4,
    "maxItems": 4,
    "description": "[west, south, east, north] in degrees; west > east crosses the antimeridian",
}

DATA_TOOLS: list[dict[str, Any]] = [
    {
        "name": "search_events",
        "description": "Find disaster events by text (title/region), type, severity, area and time. Newest first.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Words in the title or region, e.g. 'Japan' or 'Polo'"},
                "bbox": _BBOX,
                "limit": {"type": "integer", "minimum": 1, "maximum": MAX_RESULTS},
                **_FILTER_PROPS,
            },
        },
    },
    {
        "name": "view_summary",
        "description": "Totals by severity and type, affected population and data age for an area (default: the user's current view).",
        "input_schema": {"type": "object", "properties": {"bbox": _BBOX, **_FILTER_PROPS}},
    },
    {
        "name": "nearby_events",
        "description": "Events around a point, nearest first, with distance in km.",
        "input_schema": {
            "type": "object",
            "properties": {
                "lat": {"type": "number"},
                "lng": {"type": "number"},
                "radius_km": {"type": "number", "minimum": 1, "maximum": 5000},
                "limit": {"type": "integer", "minimum": 1, "maximum": MAX_RESULTS},
                **_FILTER_PROPS,
            },
            "required": ["lat", "lng"],
        },
    },
    {
        "name": "get_event",
        "description": "Full details of one event (description, sources, dates, population).",
        "input_schema": {
            "type": "object",
            "properties": {"event_id": {"type": "string", "format": "uuid"}},
            "required": ["event_id"],
        },
    },
]

MAP_TOOLS: list[dict[str, Any]] = [
    {
        "name": "fly_to",
        "description": "Move the user's map camera.",
        "input_schema": {
            "type": "object",
            "properties": {
                "lat": {"type": "number"},
                "lng": {"type": "number"},
                "zoom": {"type": "number", "minimum": 0, "maximum": 18, "description": "2 world, 5 country, 8 region, 12 city"},
            },
            "required": ["lat", "lng"],
        },
    },
    {
        "name": "set_layers",
        "description": "Show or hide map overlay layers. Only ids from available_layers in the context are valid.",
        "input_schema": {
            "type": "object",
            "properties": {
                "show": {"type": "array", "items": {"type": "string"}},
                "hide": {"type": "array", "items": {"type": "string"}},
            },
        },
    },
    {
        "name": "set_event_filters",
        "description": "Choose which event types and severities the map shows. Omit a list to show all of it.",
        "input_schema": {"type": "object", "properties": {k: _FILTER_PROPS[k] for k in ("types", "severities")}},
    },
    {
        "name": "set_time",
        "description": "Move the map's timeline to an instant (ISO 8601), or back to live with at = null.",
        "input_schema": {
            "type": "object",
            "properties": {"at": {"type": ["string", "null"]}},
            "required": ["at"],
        },
    },
    {
        "name": "select_event",
        "description": "Open an event's card on the map and fly to it.",
        "input_schema": {
            "type": "object",
            "properties": {"event_id": {"type": "string", "format": "uuid"}},
            "required": ["event_id"],
        },
    },
    {
        "name": "play_brief",
        "description": "Play the Disaster Brief (a short guided map story) for an event.",
        "input_schema": {
            "type": "object",
            "properties": {"event_id": {"type": "string", "format": "uuid"}},
            "required": ["event_id"],
        },
    },
]

TOOLS = DATA_TOOLS + MAP_TOOLS
MAP_TOOL_NAMES = {tool["name"] for tool in MAP_TOOLS}
_action_adapter: TypeAdapter[MapAction] = TypeAdapter(MapAction)


class ToolError(Exception):
    """Reported back to the model as an error result."""


class _FilterArgs(BaseModel):
    types: list[EventType] | None = None
    severities: list[SeverityLevel] | None = None
    at: datetime | None = None
    bbox: list[float] | None = None


def _filter(args: dict[str, Any], context: MapContext, default_bbox: bool) -> EventFilter:
    try:
        parsed = _FilterArgs.model_validate(args)
    except ValidationError as e:
        raise ToolError(f"invalid filter: {e.errors()[0]['msg']}") from e
    bbox = parsed.bbox or (context.bbox if default_bbox else None)
    box: dict[str, float] = {}
    if bbox:
        if len(bbox) != 4:
            raise ToolError("bbox needs 4 numbers")
        box = dict(zip(("min_lng", "min_lat", "max_lng", "max_lat"), bbox, strict=True))
    try:
        return EventFilter(
            types=parsed.types,
            severities=parsed.severities,
            at=parsed.at,
            is_active=None if parsed.at else True,
            q=args.get("query") or None,
            **box,
        )
    except ValidationError as e:
        raise ToolError(f"invalid filter: {e.errors()[0]['msg']}") from e


def _limit(args: dict[str, Any], default: int = 10) -> int:
    try:
        return max(1, min(MAX_RESULTS, int(args.get("limit", default))))
    except (TypeError, ValueError) as e:
        raise ToolError("limit must be an integer") from e


def compact_event(event: EventResponse) -> dict[str, Any]:
    return {
        "id": str(event.id),
        "title": event.title,
        "type": event.type,
        "severity": event.severity,
        "lat": event.location.lat,
        "lng": event.location.lng,
        "region": event.location.country,
        "start": event.start_date.isoformat(),
        "end": event.end_date.isoformat() if event.end_date else None,
        "affected_population": event.affected_population,
    }


async def run_data_tool(
    name: str, args: dict[str, Any], events: EventService, context: MapContext
) -> dict[str, Any]:
    if name == "search_events":
        result = await events.list_events(_filter(args, context, default_bbox=False), _limit(args), 0)
        return {"total": result.pagination.total, "events": [compact_event(e) for e in result.data]}
    if name == "view_summary":
        return (await events.summarize_view(_filter(args, context, default_bbox=True))).model_dump(mode="json")
    if name == "nearby_events":
        try:
            lat, lng = float(args["lat"]), float(args["lng"])
            radius = float(args.get("radius_km", 500))
        except (KeyError, TypeError, ValueError) as e:
            raise ToolError("lat and lng are required numbers") from e
        if not (-90 <= lat <= 90 and -180 <= lng <= 180 and 0 < radius <= 5000):
            raise ToolError("lat/lng out of range or radius_km not in (0, 5000]")
        result = await events.nearby(_filter(args, context, default_bbox=False), lat, lng, radius, _limit(args))
        return {"events": [{**compact_event(n.event), "distance_km": n.distance_km} for n in result.data]}
    if name == "get_event":
        try:
            event_id = UUID(str(args.get("event_id")))
        except ValueError as e:
            raise ToolError("event_id must be a UUID") from e
        event = await events.get_event(event_id)
        if event is None:
            raise ToolError("no event with that id")
        return {
            **compact_event(event),
            "description": (event.description or "")[:DESCRIPTION_CHARS],
            "sources": [s.name for s in event.sources],
        }
    raise ToolError(f"unknown tool {name}")


def validate_map_action(name: str, args: dict[str, Any], context: MapContext) -> MapAction:
    try:
        action = _action_adapter.validate_python({**args, "type": name})
    except ValidationError as e:
        raise ToolError(f"invalid {name}: {e.errors()[0]['msg']}") from e
    if action.type == "set_layers":
        unknown = sorted(set(action.show + action.hide) - set(context.available_layers))
        if unknown:
            raise ToolError(f"unknown layer ids {unknown}; available: {context.available_layers}")
    return action
