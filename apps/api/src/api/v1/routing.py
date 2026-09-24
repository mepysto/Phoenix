"""Hazard-aware relief and evacuation routes (M6, G-19)."""

import asyncio
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import get_settings
from src.db.database import get_db
from src.services.routing import RoutingError, ValhallaClient, plan_route

router = APIRouter()

# Fair use of a shared public router: few requests in flight per process
_in_flight = asyncio.Semaphore(4)


class Point(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)


class RouteRequest(BaseModel):
    start: Point
    end: Point
    mode: Literal["auto", "truck", "pedestrian", "bicycle"] = "auto"
    avoid_hazards: bool = True


class RouteHazard(BaseModel):
    id: str
    title: str
    severity: str
    zone_km: float
    distance_km: float


class RouteGeometry(BaseModel):
    type: Literal["LineString"] = "LineString"
    coordinates: list[list[float]]


class RouteResponse(BaseModel):
    geometry: RouteGeometry
    distance_km: float | None
    duration_min: float | None
    hazards: list[RouteHazard]
    fires_near_route: int
    avoided: bool
    # router_limit: the router cannot avoid areas this large; no_detour: none exists
    avoidance_note: Literal["router_limit", "no_detour"] | None


@router.post("/route", response_model=RouteResponse)
async def route(request: RouteRequest, session: AsyncSession = Depends(get_db)) -> RouteResponse:
    """Route between two points with the active hazards it passes (and a detour when possible)."""
    settings = get_settings()
    client = ValhallaClient(settings.valhalla_url, settings.valhalla_client_id)
    try:
        async with _in_flight:
            plan = await plan_route(
                session,
                client,
                (request.start.lat, request.start.lng),
                (request.end.lat, request.end.lng),
                request.mode,
                request.avoid_hazards,
                settings.valhalla_max_exclude_circumference_m,
            )
    except RoutingError as e:
        raise HTTPException(status_code=422 if e.no_route else 502, detail=str(e)) from e
    return RouteResponse(
        geometry=RouteGeometry(coordinates=[[lng, lat] for lng, lat in plan["coordinates"]]),
        distance_km=plan["length_km"],
        duration_min=round(plan["time_s"] / 60, 1) if plan["time_s"] is not None else None,
        hazards=[
            RouteHazard(id=h.id, title=h.title, severity=h.severity, zone_km=h.zone_km, distance_km=h.distance_km)
            for h in plan["hazards"]
        ],
        fires_near_route=plan["fires_near_route"],
        avoided=plan["avoided"],
        avoidance_note=plan["avoidance_note"],
    )
