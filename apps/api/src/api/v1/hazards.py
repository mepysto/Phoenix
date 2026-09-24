"""Live hazard layers for the map (public, cached, keyless upstreams)."""

from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.database import get_db
from src.models.fire import FireDetection
from src.services.hazards.firms import RETENTION_HOURS
from src.utils.geo import envelope_filter

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


MAX_FIRES = 5000


@router.get("/fires")
async def active_fires(
    response: Response,
    session: Annotated[AsyncSession, Depends(get_db)],
    min_lng: Annotated[float, Query(ge=-180, le=180)],
    min_lat: Annotated[float, Query(ge=-90, le=90)],
    max_lng: Annotated[float, Query(ge=-180, le=180)],
    max_lat: Annotated[float, Query(ge=-90, le=90)],
    hours: Annotated[int, Query(ge=1, le=RETENTION_HOURS)] = 24,
    limit: Annotated[int, Query(ge=1, le=MAX_FIRES)] = 3000,
) -> dict[str, Any]:
    """NASA FIRMS VIIRS active-fire detections in the viewport from the last
    `hours`, most intense first (fire radiative power). `truncated` means
    zoom in to see smaller fires."""
    since = datetime.now(UTC) - timedelta(hours=hours)
    rows = (
        await session.execute(
            select(
                FireDetection.latitude,
                FireDetection.longitude,
                FireDetection.frp,
                FireDetection.confidence,
                FireDetection.acquired_at,
                FireDetection.satellite,
                FireDetection.daynight,
            )
            .where(FireDetection.acquired_at >= since)
            .where(envelope_filter(FireDetection.location, min_lng, min_lat, max_lng, max_lat))
            .order_by(func.coalesce(FireDetection.frp, 0).desc())
            .limit(limit + 1)
        )
    ).all()
    response.headers["Cache-Control"] = "public, max-age=600"
    return {
        "type": "FeatureCollection",
        "truncated": len(rows) > limit,
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [r.longitude, r.latitude]},
                "properties": {
                    "frp": r.frp,
                    "confidence": r.confidence,
                    "acquired_at": r.acquired_at.isoformat(),
                    "satellite": r.satellite,
                    "daynight": r.daynight,
                },
            }
            for r in rows[:limit]
        ],
    }
