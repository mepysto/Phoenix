"""Public traffic cameras and their snapshot proxy (M6, G-10)."""

import asyncio
import math
import time
from collections import OrderedDict
from typing import Any

from fastapi import APIRouter, HTTPException, Path, Query, Response
from pydantic import BaseModel

from src.services.cameras.caltrans import SNAPSHOT_HOSTS, Camera, caltrans_cameras
from src.utils.safe_fetch import UnsafeFetch, safe_get

router = APIRouter()

MAX_SNAPSHOT_BYTES = 2_000_000
SNAPSHOT_TIMEOUT_SECONDS = 10
SNAPSHOT_CACHE_SECONDS = 60  # upstream images refresh every few minutes
SNAPSHOT_CACHE_ENTRIES = 500
# Upstream fetches in flight at once, across all viewers
_upstream = asyncio.Semaphore(8)
_snapshots: OrderedDict[str, tuple[float, bytes, str]] = OrderedDict()


def _feature(camera: Camera) -> dict[str, Any]:
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [camera.longitude, camera.latitude]},
        "properties": {
            "id": camera.id,
            "name": camera.name,
            "direction": camera.direction,
            "route": camera.route,
            "source": camera.source,
            "snapshot_minutes": camera.snapshot_minutes,
        },
    }


def _in_bbox(camera: Camera, west: float, south: float, east: float, north: float) -> bool:
    if not south <= camera.latitude <= north:
        return False
    if west <= east:
        return west <= camera.longitude <= east
    return camera.longitude >= west or camera.longitude <= east  # crosses the antimeridian


def _distance_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    h = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lng2 - lng1) / 2) ** 2
    return 2 * 6371 * math.asin(min(1.0, math.sqrt(h)))


@router.get("")
async def cameras_in_view(
    response: Response,
    min_lng: float = Query(..., ge=-180, le=180),
    min_lat: float = Query(..., ge=-90, le=90),
    max_lng: float = Query(..., ge=-180, le=180),
    max_lat: float = Query(..., ge=-90, le=90),
    limit: int = Query(default=5000, ge=1, le=5000),
) -> dict[str, Any]:
    """Public traffic cameras in a bbox (GeoJSON)."""
    cameras = await caltrans_cameras.all()
    inside = [c for c in cameras if _in_bbox(c, min_lng, min_lat, max_lng, max_lat)][:limit]
    response.headers["Cache-Control"] = "public, max-age=300"
    return {"type": "FeatureCollection", "features": [_feature(c) for c in inside]}


class NearbyCamera(BaseModel):
    id: str
    name: str
    direction: str | None
    source: str
    distance_km: float


@router.get("/nearby", response_model=list[NearbyCamera])
async def cameras_nearby(
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
    radius_km: float = Query(default=25, gt=0, le=200),
    limit: int = Query(default=10, ge=1, le=50),
) -> list[NearbyCamera]:
    """Cameras closest to a point (e.g. an event), nearest first."""
    cameras = await caltrans_cameras.all()
    ranked = sorted(
        ((c, _distance_km(lat, lng, c.latitude, c.longitude)) for c in cameras),
        key=lambda pair: pair[1],
    )
    return [
        NearbyCamera(id=c.id, name=c.name, direction=c.direction, source=c.source, distance_km=round(d, 1))
        for c, d in ranked[:limit]
        if d <= radius_km
    ]


@router.get(
    "/{camera_id}/snapshot",
    responses={200: {"content": {"image/jpeg": {}}}, 404: {}, 502: {}},
    response_class=Response,
)
async def camera_snapshot(
    camera_id: str = Path(..., pattern=r"^[a-z]+-d\d{1,2}-\d{1,6}$"),
) -> Response:
    """Latest still image of a camera, fetched by the server (never by URL from the client)."""
    now = time.monotonic()
    cached = _snapshots.get(camera_id)
    if cached and now - cached[0] < SNAPSHOT_CACHE_SECONDS:
        return _image(cached[1], cached[2])
    camera = await caltrans_cameras.get(camera_id)
    if camera is None:
        raise HTTPException(status_code=404, detail="Unknown camera")
    try:
        async with _upstream:
            fetched = await safe_get(
                camera.snapshot_url,
                SNAPSHOT_HOSTS,
                max_bytes=MAX_SNAPSHOT_BYTES,
                timeout_seconds=SNAPSHOT_TIMEOUT_SECONDS,
                content_type_prefix="image/",
            )
    except UnsafeFetch as e:
        if cached:  # a slightly old picture beats none
            return _image(cached[1], cached[2])
        raise HTTPException(status_code=502, detail="Camera image unavailable") from e
    _snapshots[camera_id] = (now, fetched.content, fetched.content_type)
    _snapshots.move_to_end(camera_id)
    while len(_snapshots) > SNAPSHOT_CACHE_ENTRIES:
        _snapshots.popitem(last=False)
    return _image(fetched.content, fetched.content_type)


def _image(content: bytes, content_type: str) -> Response:
    return Response(
        content=content,
        media_type=content_type,
        headers={
            "Cache-Control": f"public, max-age={SNAPSHOT_CACHE_SECONDS}",
            "X-Content-Type-Options": "nosniff",
        },
    )
