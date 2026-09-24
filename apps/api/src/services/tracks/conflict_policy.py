"""Conflict-zone policy for military positions (RESPONSIBLE_USE §3).

Monitoring exists to support recovery, not targeting. In active conflict
areas, near-real-time positions of military aircraft and ships can
endanger people, so deployments can generalise them to a coarse grid
(without identity, course or speed) or hide them.
"""

import math
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.event import Event, EventType

Policy = Literal["off", "grid", "hide"]
CONFLICT_TYPES = (EventType.war, EventType.complex_emergency)
GRID_DEGREES = 1.0  # ~100 km
ZONES_TTL_SECONDS = 300
# Kept when a position is generalised; everything else (identity, motion) is dropped
GENERALISED_PROPERTIES = ("military",)


@dataclass
class ConflictZones:
    points: list[tuple[float, float]] = field(default_factory=list)
    radius_km: float = 150
    boxes: list[list[float]] = field(default_factory=list)

    def contains(self, lat: float, lng: float) -> bool:
        for west, south, east, north in self.boxes:
            inside_lng = west <= lng <= east if west <= east else (lng >= west or lng <= east)
            if south <= lat <= north and inside_lng:
                return True
        return any(_distance_km(lat, lng, z_lat, z_lng) <= self.radius_km for z_lat, z_lng in self.points)


def _distance_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    h = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lng2 - lng1) / 2) ** 2
    return 2 * 6371 * math.asin(min(1.0, math.sqrt(h)))


def _snap(value: float) -> float:
    return math.floor(value / GRID_DEGREES) * GRID_DEGREES + GRID_DEGREES / 2


def apply_policy(
    features: Iterable[dict[str, Any]],
    policy: Policy,
    zones: ConflictZones,
    is_military: Callable[[dict[str, Any]], bool],
) -> list[dict[str, Any]]:
    """Generalise or drop military features inside conflict zones; others pass unchanged."""
    result = []
    for feature in features:
        if policy == "off" or not is_military(feature.get("properties") or {}):
            result.append(feature)
            continue
        lng, lat = feature["geometry"]["coordinates"][:2]
        if not zones.contains(lat, lng):
            result.append(feature)
        elif policy == "grid":
            props = feature.get("properties") or {}
            result.append(
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [_snap(lng), _snap(lat)]},
                    "properties": {**{k: props.get(k) for k in GENERALISED_PROPERTIES}, "generalised": True},
                }
            )
        # policy == "hide": dropped
    return result


class ConflictZoneCache:
    """Zones from active conflict events, refreshed every few minutes per process."""

    def __init__(self) -> None:
        self._points: list[tuple[float, float]] = []
        self._loaded_at = 0.0

    async def zones(self, session: AsyncSession, radius_km: float, boxes: list[list[float]]) -> ConflictZones:
        if time.monotonic() - self._loaded_at > ZONES_TTL_SECONDS:
            rows = await session.execute(
                select(Event.latitude, Event.longitude).where(
                    Event.type.in_(CONFLICT_TYPES),
                    Event.is_active.is_(True),
                    Event.is_canonical.is_(True),
                    Event.latitude.isnot(None),
                    Event.longitude.isnot(None),
                )
            )
            self._points = [(lat, lng) for lat, lng in rows.all()]
            self._loaded_at = time.monotonic()
        return ConflictZones(points=self._points, radius_km=radius_km, boxes=boxes)


conflict_zone_cache = ConflictZoneCache()
