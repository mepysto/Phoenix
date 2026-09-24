"""Live hazard layers for the map (public, cached, keyless upstreams)."""

from typing import Any

from fastapi import APIRouter, Response

from src.services.hazards.nhc_cyclones import CACHE_TTL_SECONDS, nhc_cyclone_service
from src.services.hazards.usgs_shakemaps import usgs_shakemap_service

router = APIRouter()


@router.get("/cyclones")
async def active_cyclones(response: Response) -> dict[str, Any]:
    """Active tropical cyclones (NHC basins): forecast cone, track, positions
    and past track as GeoJSON. Cached for 10 minutes; `stale` is true when
    NOAA is unreachable and the last good data is being served."""
    response.headers["Cache-Control"] = f"public, max-age={CACHE_TTL_SECONDS // 2}"
    return await nhc_cyclone_service.get_cyclones()


@router.get("/shakemaps")
async def recent_shakemaps(response: Response) -> dict[str, Any]:
    """Shaking-intensity (MMI IV+) contours for the past week's M4.5+
    earthquakes that have a USGS ShakeMap, strongest shaking first.
    Cached for 10 minutes; `stale` marks cached data served during an outage."""
    response.headers["Cache-Control"] = f"public, max-age={CACHE_TTL_SECONDS // 2}"
    return await usgs_shakemap_service.get_shakemaps()
