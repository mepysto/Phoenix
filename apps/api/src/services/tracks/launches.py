"""Upcoming space launches (Launch Library 2, The Space Devs) (G-20).

Complements the satellite layer: new Earth-observation and communications
satellites heading for orbit, and launch activity near an affected area.
The free API allows 15 calls per hour, so the list is cached for an hour.
Credit: The Space Devs.
"""

from typing import Any

import httpx

from src.services.hazards.cache import StaleOnErrorCache

UPCOMING_URL = "https://ll.thespacedevs.com/2.3.0/launches/upcoming/"
CACHE_TTL_SECONDS = 3600
RETRY_AFTER_ERROR_SECONDS = 1200
REQUEST_TIMEOUT = httpx.Timeout(30.0, connect=10.0)
USER_AGENT = "Phoenix-disaster-map/0.1 (+https://github.com/mepysto/Phoenix)"
LIMIT = 30


def _get(obj: Any, *path: str) -> Any:
    for key in path:
        if not isinstance(obj, dict):
            return None
        obj = obj.get(key)
    return obj


def to_geojson(payload: dict[str, Any]) -> dict[str, Any]:
    """LL2 launches → points at their pads; launches without a pad position are dropped."""
    features = []
    for launch in payload.get("results") or []:
        lat, lng = _get(launch, "pad", "latitude"), _get(launch, "pad", "longitude")
        try:
            lat, lng = float(lat), float(lng)
        except (TypeError, ValueError):
            continue
        if not (-90 <= lat <= 90 and -180 <= lng <= 180):
            continue
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [round(lng, 5), round(lat, 5)]},
                "properties": {
                    "id": launch.get("id"),
                    "name": launch.get("name"),
                    "net": launch.get("net"),
                    "status": _get(launch, "status", "abbrev"),
                    "provider": _get(launch, "launch_service_provider", "abbrev")
                    or _get(launch, "launch_service_provider", "name"),
                    "mission_type": _get(launch, "mission", "type"),
                    "orbit": _get(launch, "mission", "orbit", "abbrev"),
                    "pad": _get(launch, "pad", "name"),
                },
            }
        )
    return {"type": "FeatureCollection", "features": features}


class LaunchService:
    def __init__(self) -> None:
        self._cache = StaleOnErrorCache(
            "Launch Library 2", CACHE_TTL_SECONDS, retry_after_error_seconds=RETRY_AFTER_ERROR_SECONDS
        )

    async def _fetch(self) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT, headers={"User-Agent": USER_AGENT}) as client:
            response = await client.get(UPCOMING_URL, params={"limit": LIMIT, "mode": "normal"})
            response.raise_for_status()
            return to_geojson(response.json())

    async def upcoming(self) -> dict[str, Any]:
        return await self._cache.get(self._fetch)


launch_service = LaunchService()
