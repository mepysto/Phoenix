"""Moving things worth watching during a response (M5): satellites for now."""

from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Query, Response
from pydantic import BaseModel

from src.services.tracks.satellites import CACHE_TTL_SECONDS, satellite_service

router = APIRouter()

MAX_PASSES = 50


class SatellitePass(BaseModel):
    name: str
    norad_id: int
    rise: datetime
    culmination: datetime
    set: datetime
    max_elevation_deg: float
    daylight: bool


class SatellitePassesResponse(BaseModel):
    lat: float
    lng: float
    start: datetime
    hours: float
    min_elevation_deg: float
    passes: list[SatellitePass]


@router.get("/satellites")
async def satellite_positions(
    response: Response,
    at: Annotated[datetime | None, Query(description="Instant (default now)")] = None,
) -> dict[str, Any]:
    """Sub-satellite points of Earth-observation satellites (CelesTrak, SGP4)."""
    when = (at or datetime.now(UTC)).astimezone(UTC)
    response.headers["Cache-Control"] = "public, max-age=15"
    return await satellite_service.positions(when)


@router.get("/satellites/passes", response_model=SatellitePassesResponse)
async def satellite_passes(
    response: Response,
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
    hours: float = Query(default=24, gt=0, le=48),
    min_elevation: float = Query(default=30, ge=10, le=90, description="Degrees above the horizon"),
    daylight_only: bool = Query(default=False, description="Only passes useful to optical imagers"),
) -> SatellitePassesResponse:
    """Upcoming passes of Earth-observation satellites over a place, soonest first."""
    start = datetime.now(UTC)
    passes = await satellite_service.passes(lat, lng, start, hours, min_elevation)
    if daylight_only:
        passes = [p for p in passes if p.daylight]
    upcoming = [p for p in passes if p.set >= start][:MAX_PASSES]
    response.headers["Cache-Control"] = f"public, max-age={min(600, CACHE_TTL_SECONDS)}"
    return SatellitePassesResponse(
        lat=lat,
        lng=lng,
        start=start,
        hours=hours,
        min_elevation_deg=min_elevation,
        passes=[SatellitePass(**p.__dict__) for p in upcoming],
    )
