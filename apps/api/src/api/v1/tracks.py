"""Moving things worth watching during a response (M5): satellites, aircraft, ships, launches."""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import get_settings
from src.db.database import get_db
from src.services.tracks.aircraft import MAX_RADIUS_NM, aircraft_service
from src.services.tracks.conflict_policy import apply_policy, conflict_zone_cache
from src.services.tracks.launches import launch_service
from src.services.tracks.satellites import CACHE_TTL_SECONDS, satellite_service
from src.services.tracks.vessels import vessels_geojson

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


@router.get("/aircraft")
async def aircraft_around(
    response: Response,
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
    radius_nm: float = Query(default=100, gt=0, le=MAX_RADIUS_NM, description="Nautical miles"),
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Aircraft (ADS-B, adsb.lol) around a point; privacy-programme aircraft are excluded."""
    response.headers["Cache-Control"] = "public, max-age=10"
    collection = await aircraft_service.around(lat, lng, radius_nm)
    return await _conflict_policy(collection, session, lambda p: p.get("military") is True)


VESSEL_MAX_AGE = timedelta(minutes=30)
VESSEL_LIMIT = 3000


@router.get("/vessels")
async def vessels_in_view(
    response: Response,
    min_lng: float = Query(..., ge=-180, le=180),
    min_lat: float = Query(..., ge=-90, le=90),
    max_lng: float = Query(..., ge=-180, le=180),
    max_lat: float = Query(..., ge=-90, le=90),
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Ships (AIS) reported in the last 30 min around active high/critical events.

    `enabled` is false when the server has no AISStream key (the list is then empty).
    """
    response.headers["Cache-Control"] = "public, max-age=10"
    enabled = get_settings().aisstream_api_key is not None
    collection = await vessels_geojson(
        session, (min_lng, min_lat, max_lng, max_lat), VESSEL_MAX_AGE, VESSEL_LIMIT
    )
    collection = await _conflict_policy(collection, session, lambda p: p.get("ship_type") == AIS_MILITARY)
    return {**collection, "enabled": enabled}


@router.get("/launches")
async def upcoming_launches(response: Response) -> dict[str, Any]:
    """Upcoming (and just-flown) space launches at their pads (Launch Library 2, The Space Devs)."""
    response.headers["Cache-Control"] = "public, max-age=1800"
    return await launch_service.upcoming()


AIS_MILITARY = 35  # AIS ship type "military operations"


async def _conflict_policy(
    collection: dict[str, Any], session: AsyncSession, is_military: Callable[[dict[str, Any]], bool]
) -> dict[str, Any]:
    """Apply the deployment's conflict-zone policy to military positions (RESPONSIBLE_USE §3)."""
    settings = get_settings()
    if settings.conflict_zone_policy == "off":
        return collection
    zones = await conflict_zone_cache.zones(
        session, settings.conflict_zone_radius_km, settings.conflict_zone_bboxes
    )
    features = apply_policy(collection.get("features") or [], settings.conflict_zone_policy, zones, is_military)
    return {**collection, "features": features}
