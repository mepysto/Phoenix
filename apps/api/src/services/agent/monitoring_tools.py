"""Agent data tools for the monitoring features (satellites, cameras, radio, routes)."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import get_settings
from src.services.cameras.caltrans import caltrans_cameras
from src.services.radio import radio_service
from src.services.routing import RoutingError, ValhallaClient, plan_route
from src.services.tracks.satellites import satellite_service

_POINT = {"lat": {"type": "number"}, "lng": {"type": "number"}}

MONITORING_TOOLS: list[dict[str, Any]] = [
    {
        "name": "satellite_passes",
        "description": "When Earth-observation satellites (Sentinel, Landsat, ...) next pass over a place: time, peak elevation, and whether it is daylight (optical imagery needs daylight, radar does not).",
        "input_schema": {
            "type": "object",
            "properties": {**_POINT, "hours": {"type": "number", "minimum": 1, "maximum": 48}},
            "required": ["lat", "lng"],
        },
    },
    {
        "name": "nearby_cameras",
        "description": "Public traffic cameras near a point (California only for now), nearest first, with ids usable by open_camera.",
        "input_schema": {
            "type": "object",
            "properties": {**_POINT, "radius_km": {"type": "number", "minimum": 1, "maximum": 200}},
            "required": ["lat", "lng"],
        },
    },
    {
        "name": "local_radio",
        "description": "Radio stations near a point; on_air=false means the station failed its last check (possible outage).",
        "input_schema": {
            "type": "object",
            "properties": {**_POINT, "radius_km": {"type": "number", "minimum": 1, "maximum": 300}},
            "required": ["lat", "lng"],
        },
    },
    {
        "name": "route_hazards",
        "description": "Plan a road route between two points and list the active high/critical hazard zones and fires along it. Use show_route to draw it for the user.",
        "input_schema": {
            "type": "object",
            "properties": {
                "start": {"type": "object", "properties": _POINT, "required": ["lat", "lng"]},
                "end": {"type": "object", "properties": _POINT, "required": ["lat", "lng"]},
                "mode": {"type": "string", "enum": ["auto", "truck", "pedestrian", "bicycle"]},
            },
            "required": ["start", "end"],
        },
    },
]
MONITORING_TOOL_NAMES = {tool["name"] for tool in MONITORING_TOOLS}


class MonitoringToolError(Exception):
    pass


def _point(value: Any, name: str = "point") -> tuple[float, float]:
    try:
        lat, lng = float(value["lat"]), float(value["lng"])
    except (KeyError, TypeError, ValueError) as e:
        raise MonitoringToolError(f"{name} needs numeric lat and lng") from e
    if not (-90 <= lat <= 90 and -180 <= lng <= 180):
        raise MonitoringToolError(f"{name} is out of range")
    return lat, lng


def _bounded(value: Any, default: float, low: float, high: float) -> float:
    try:
        return min(high, max(low, float(value if value is not None else default)))
    except (TypeError, ValueError) as e:
        raise MonitoringToolError("expected a number") from e


async def run_monitoring_tool(name: str, args: dict[str, Any], session: AsyncSession) -> dict[str, Any]:
    if name == "satellite_passes":
        lat, lng = _point(args)
        hours = _bounded(args.get("hours"), 24, 1, 48)
        passes = await satellite_service.passes(lat, lng, datetime.now(UTC), hours, 30)
        return {
            "passes": [
                {
                    "satellite": p.name,
                    "peak": p.culmination.isoformat(timespec="minutes"),
                    "max_elevation_deg": p.max_elevation_deg,
                    "daylight": p.daylight,
                }
                for p in passes[:12]
            ]
        }
    if name == "nearby_cameras":
        lat, lng = _point(args)
        radius = _bounded(args.get("radius_km"), 25, 1, 200)
        return {
            "cameras": [
                {"id": c.id, "name": c.name, "direction": c.direction, "distance_km": round(d, 1)}
                for c, d in await caltrans_cameras.nearest(lat, lng, radius, 10)
            ]
        }
    if name == "local_radio":
        lat, lng = _point(args)
        radius = _bounded(args.get("radius_km"), 150, 1, 300)
        stations = await radio_service.nearby(lat, lng, radius, 8)
        return {
            "stations": [
                {k: s[k] for k in ("name", "language", "distance_km", "on_air", "country_code")} for s in stations
            ]
        }
    if name == "route_hazards":
        start, end = _point(args.get("start"), "start"), _point(args.get("end"), "end")
        mode = args.get("mode") or "auto"
        if mode not in ("auto", "truck", "pedestrian", "bicycle"):
            raise MonitoringToolError("unknown mode")
        settings = get_settings()
        try:
            plan = await plan_route(
                session,
                ValhallaClient(settings.valhalla_url, settings.valhalla_client_id),
                start,
                end,
                mode,
                True,
                settings.valhalla_max_exclude_circumference_m,
            )
        except RoutingError as e:
            raise MonitoringToolError(str(e)) from e
        return {
            "distance_km": plan["length_km"],
            "duration_min": round(plan["time_s"] / 60) if plan["time_s"] is not None else None,
            "hazards": [
                {"title": h.title, "severity": h.severity, "distance_km": h.distance_km} for h in plan["hazards"]
            ],
            "fires_near_route": plan["fires_near_route"],
            "hazard_zones_avoided": plan["avoided"],
            "note": plan["avoidance_note"],
        }
    raise MonitoringToolError(f"unknown tool {name}")
