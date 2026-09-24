"""Public traffic cameras (G-10), first source: Caltrans (California), public domain.

Cameras let responders see conditions on the ground: flooding on a road,
smoke, a collapsed overpass, evacuation traffic. Snapshots are served
through our proxy (GET /cameras/{id}/snapshot); clients never send URLs.
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

import httpx

from src.services.hazards.cache import StaleOnErrorCache

logger = logging.getLogger(__name__)

DISTRICTS = range(1, 13)
LIST_URL = "https://cwwp2.dot.ca.gov/data/d{d}/cctv/cctvStatusD{d:02d}.json"
# Hosts the snapshot proxy may contact for this source
SNAPSHOT_HOSTS = frozenset({"cwwp2.dot.ca.gov"})
CACHE_TTL_SECONDS = 3600  # camera lists change rarely
RETRY_AFTER_ERROR_SECONDS = 600
REQUEST_TIMEOUT = httpx.Timeout(30.0, connect=10.0)
USER_AGENT = "Phoenix-disaster-map/0.1 (+https://github.com/mepysto/Phoenix)"


@dataclass(frozen=True)
class Camera:
    id: str  # "caltrans-d4-1"
    name: str
    latitude: float
    longitude: float
    direction: str | None  # North/South/East/West as reported
    route: str | None
    snapshot_url: str
    snapshot_minutes: int | None  # how often the image refreshes upstream
    source: str = "Caltrans"


def _float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_district(payload: dict[str, Any], district: int) -> list[Camera]:
    cameras = []
    for item in payload.get("data") or []:
        cctv = (item or {}).get("cctv") or {}
        location = cctv.get("location") or {}
        static = ((cctv.get("imageData") or {}).get("static")) or {}
        lat, lng = _float(location.get("latitude")), _float(location.get("longitude"))
        url = static.get("currentImageURL") or ""
        if (
            cctv.get("inService") != "true"
            or lat is None
            or lng is None
            or not (-90 <= lat <= 90 and -180 <= lng <= 180)
            or not url.startswith("https://cwwp2.dot.ca.gov/")
        ):
            continue
        frequency = _float(static.get("currentImageUpdateFrequency"))
        cameras.append(
            Camera(
                id=f"caltrans-d{district}-{cctv.get('index')}",
                name=str(location.get("locationName") or "Camera")[:120],
                latitude=lat,
                longitude=lng,
                direction=(location.get("direction") or None),
                route=(location.get("route") or None),
                snapshot_url=url,
                snapshot_minutes=int(frequency) if frequency else None,
            )
        )
    return cameras


class CaltransCameras:
    def __init__(self) -> None:
        self._cache = StaleOnErrorCache(
            "Caltrans CCTV", CACHE_TTL_SECONDS, retry_after_error_seconds=RETRY_AFTER_ERROR_SECONDS
        )
        self._by_id: dict[str, Camera] = {}
        self._list_version: object | None = None

    async def _fetch(self) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT, headers={"User-Agent": USER_AGENT}) as client:

            async def district(d: int) -> list[Camera]:
                try:
                    response = await client.get(LIST_URL.format(d=d))
                    response.raise_for_status()
                    return parse_district(response.json(), d)
                except (httpx.HTTPError, ValueError) as e:
                    logger.warning("Caltrans district %d camera list failed: %r", d, e)
                    return []

            results = await asyncio.gather(*(district(d) for d in DISTRICTS))
        cameras = [camera for batch in results for camera in batch]
        if not cameras:
            raise ValueError("no Caltrans cameras loaded")
        return {"cameras": cameras}

    async def all(self) -> list[Camera]:
        data = await self._cache.get(self._fetch)
        cameras: list[Camera] = data["cameras"]
        if data is not self._list_version:
            self._by_id = {camera.id: camera for camera in cameras}
            self._list_version = data
        return cameras

    async def get(self, camera_id: str) -> Camera | None:
        await self.all()
        return self._by_id.get(camera_id)


caltrans_cameras = CaltransCameras()
