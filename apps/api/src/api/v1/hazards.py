"""Live hazard layers for the map (public, cached, keyless upstreams)."""

from typing import Any

from fastapi import APIRouter, Response

from src.services.hazards.nhc_cyclones import CACHE_TTL_SECONDS, nhc_cyclone_service

router = APIRouter()


@router.get("/cyclones")
async def active_cyclones(response: Response) -> dict[str, Any]:
    """Active tropical cyclones (NHC basins): forecast cone, track, positions
    and past track as GeoJSON. Cached for 10 minutes; `stale` is true when
    NOAA is unreachable and the last good data is being served."""
    response.headers["Cache-Control"] = f"public, max-age={CACHE_TTL_SECONDS // 2}"
    return await nhc_cyclone_service.get_cyclones()
