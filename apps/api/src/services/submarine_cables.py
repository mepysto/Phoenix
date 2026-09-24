"""Submarine cables and landing stations (TeleGeography Submarine Cable Map).

Why: after earthquakes, landslides and storms, damaged cables and landing
stations cut whole regions off the internet; knowing which cables land
near an affected coast guides communications recovery.

Licence: CC BY-NC-SA 3.0 (non-commercial deployments only). The files
change rarely, so they are cached for a day and coordinates are rounded
(~100 m) to shrink the ~750 KB download.
"""

from typing import Any

import httpx

from src.services.hazards.cache import StaleOnErrorCache, round_coords

BASE = "https://www.submarinecablemap.com/api/v3"
CABLES_URL = f"{BASE}/cable/cable-geo.json"
LANDINGS_URL = f"{BASE}/landing-point/landing-point-geo.json"
CACHE_TTL_SECONDS = 24 * 3600
RETRY_AFTER_ERROR_SECONDS = 1800
REQUEST_TIMEOUT = httpx.Timeout(60.0, connect=10.0)
USER_AGENT = "Phoenix-disaster-map/0.1 (+https://github.com/mepysto/Phoenix)"
COORD_DIGITS = 3


def simplify(cables: dict[str, Any], landings: dict[str, Any]) -> dict[str, Any]:
    """One FeatureCollection: cable lines (name, colour) and landing points (name)."""
    features = []
    for feature in cables.get("features") or []:
        geometry = feature.get("geometry") or {}
        if geometry.get("type") not in ("LineString", "MultiLineString"):
            continue
        props = feature.get("properties") or {}
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": geometry["type"], "coordinates": round_coords(geometry.get("coordinates"), COORD_DIGITS)},
                "properties": {
                    "kind": "cable",
                    "id": props.get("id"),
                    "name": props.get("name"),
                    "color": props.get("color") or "#94a3b8",
                },
            }
        )
    for feature in landings.get("features") or []:
        geometry = feature.get("geometry") or {}
        props = feature.get("properties") or {}
        if geometry.get("type") != "Point" or props.get("is_tbd"):
            continue
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": round_coords(geometry.get("coordinates"), COORD_DIGITS)},
                "properties": {"kind": "landing", "id": props.get("id"), "name": props.get("name")},
            }
        )
    if not features:
        raise ValueError("no submarine cable features")
    return {"type": "FeatureCollection", "features": features}


class SubmarineCableService:
    def __init__(self) -> None:
        self._cache = StaleOnErrorCache(
            "Submarine Cable Map", CACHE_TTL_SECONDS, retry_after_error_seconds=RETRY_AFTER_ERROR_SECONDS
        )

    async def _fetch(self) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT, headers={"User-Agent": USER_AGENT}) as client:
            cables = await client.get(CABLES_URL)
            cables.raise_for_status()
            landings = await client.get(LANDINGS_URL)
            landings.raise_for_status()
            return simplify(cables.json(), landings.json())

    async def get(self) -> dict[str, Any]:
        return await self._cache.get(self._fetch)


submarine_cable_service = SubmarineCableService()
