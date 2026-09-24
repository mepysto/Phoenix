"""Relief and evacuation routes that know about hazards (G-19).

A route comes from Valhalla. We then look for hazards along it in PostGIS:
active high/critical events whose zone the route enters, and satellite fire
detections within 2 km. When the router allows large enough avoided areas
(self-hosted Valhalla), the route is recomputed around the event zones;
the public demo server caps avoided areas at 10 km circumference, so there
the answer is the plain route with warnings.

Event zones are circles sized by severity: a coarse stand-in until real
footprints (ShakeMap contours, flood extents, cyclone cones) are used.
"""

import math
from dataclasses import dataclass
from typing import Any

import httpx
from sqlalchemy import Float, case, cast, func, literal, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.event import Event, SeverityLevel
from src.models.fire import FireDetection

ZONE_RADIUS_KM = {SeverityLevel.critical: 25.0, SeverityLevel.high: 10.0}
FIRE_BUFFER_KM = 2.0
MAX_EVENT_HAZARDS = 20
REQUEST_TIMEOUT = httpx.Timeout(30.0, connect=10.0)
COSTING = {"auto", "truck", "pedestrian", "bicycle"}


# Valhalla errors meaning "no route between these points" (not a server failure)
NO_ROUTE_ERROR_CODES = {154, 170, 171, 442, 443}  # 154: over the distance limit


class RoutingError(Exception):
    """The router failed, or (no_route=True) there is no route between the points."""

    def __init__(self, message: str, no_route: bool = False) -> None:
        super().__init__(message)
        self.no_route = no_route


@dataclass(frozen=True)
class EventHazard:
    id: str
    title: str
    severity: str
    lat: float
    lng: float
    zone_km: float
    distance_km: float


def decode_polyline6(encoded: str) -> list[tuple[float, float]]:
    """Valhalla's encoded shape (precision 6) → [(lng, lat), ...]."""
    coords, index, lat, lng = [], 0, 0, 0
    while index < len(encoded):
        values = []
        for _ in range(2):
            shift, result = 0, 0
            while True:
                byte = ord(encoded[index]) - 63
                index += 1
                result |= (byte & 0x1F) << shift
                shift += 5
                if byte < 0x20:
                    break
            values.append(~(result >> 1) if result & 1 else result >> 1)
        lat += values[0]
        lng += values[1]
        coords.append((lng / 1e6, lat / 1e6))
    return coords


def circle(lat: float, lng: float, radius_km: float, sides: int = 16) -> list[list[float]]:
    """Closed ring approximating a circle, as Valhalla [lng, lat] pairs."""
    ring = []
    for i in range(sides + 1):
        angle = 2 * math.pi * i / sides
        ring.append(
            [
                round(lng + radius_km / (111.32 * math.cos(math.radians(lat))) * math.cos(angle), 5),
                round(lat + radius_km / 110.57 * math.sin(angle), 5),
            ]
        )
    return ring


def circumference_m(radius_km: float) -> float:
    return 2 * math.pi * radius_km * 1000


class ValhallaClient:
    def __init__(self, base_url: str, client_id: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.headers = {
            "X-Client-Id": client_id,
            "User-Agent": "Phoenix-disaster-map/0.1 (+https://github.com/mepysto/Phoenix)",
        }

    async def route(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
        costing: str,
        exclude: list[list[list[float]]] | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "locations": [{"lat": start[0], "lon": start[1]}, {"lat": end[0], "lon": end[1]}],
            "costing": costing,
            "units": "kilometers",
            "directions_type": "none",
        }
        if exclude:
            body["exclude_polygons"] = exclude
        try:
            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT, headers=self.headers) as client:
                response = await client.post(f"{self.base_url}/route", json=body)
        except httpx.HTTPError as e:
            raise RoutingError("routing service unavailable") from e
        if response.status_code != 200:
            try:
                error = response.json()
            except ValueError:
                error = {}
            raise RoutingError(
                str(error.get("error") or f"routing failed ({response.status_code})"),
                no_route=error.get("error_code") in NO_ROUTE_ERROR_CODES,
            )
        trip = response.json().get("trip") or {}
        legs = trip.get("legs") or []
        coords = [c for leg in legs for c in decode_polyline6(leg.get("shape", ""))]
        summary = trip.get("summary") or {}
        if len(coords) < 2:
            raise RoutingError("no route found", no_route=True)
        return {"coordinates": coords, "length_km": summary.get("length"), "time_s": summary.get("time")}


def _line_wkt(coords: list[tuple[float, float]]) -> str:
    return "LINESTRING(" + ",".join(f"{lng} {lat}" for lng, lat in coords) + ")"


async def event_hazards(session: AsyncSession, coords: list[tuple[float, float]]) -> list[EventHazard]:
    """Active high/critical events whose zone the route enters, nearest first."""
    line = func.geography(func.ST_GeomFromText(_line_wkt(coords), 4326))
    radius_km = case(
        *((Event.severity == severity, literal(km)) for severity, km in ZONE_RADIUS_KM.items()),
        else_=literal(0.0),
    )
    distance_km = cast(func.ST_Distance(func.geography(Event.location), line) / 1000, Float)
    rows = await session.execute(
        select(Event, distance_km, radius_km)
        .where(
            Event.is_active.is_(True),
            Event.is_canonical.is_(True),
            Event.location.isnot(None),
            Event.severity.in_(list(ZONE_RADIUS_KM)),
            func.ST_DWithin(func.geography(Event.location), line, radius_km * 1000),
        )
        .order_by(distance_km)
        .limit(MAX_EVENT_HAZARDS)
    )
    return [
        EventHazard(
            id=str(event.id),
            title=event.title,
            severity=event.severity.value,
            lat=event.latitude,
            lng=event.longitude,
            zone_km=float(zone),
            distance_km=round(float(distance), 1),
        )
        for event, distance, zone in rows.all()
    ]


async def fires_near(session: AsyncSession, coords: list[tuple[float, float]]) -> int:
    line = func.geography(func.ST_GeomFromText(_line_wkt(coords), 4326))
    count = await session.scalar(
        select(func.count()).where(
            func.ST_DWithin(func.geography(FireDetection.location), line, FIRE_BUFFER_KM * 1000)
        )
    )
    return int(count or 0)


async def plan_route(
    session: AsyncSession,
    router: ValhallaClient,
    start: tuple[float, float],
    end: tuple[float, float],
    costing: str,
    avoid_hazards: bool,
    max_exclude_circumference_m: float,
) -> dict[str, Any]:
    route = await router.route(start, end, costing)
    hazards = await event_hazards(session, route["coordinates"])
    avoided, note = False, None
    if avoid_hazards and hazards:
        total = sum(circumference_m(h.zone_km) for h in hazards)
        if total > max_exclude_circumference_m:
            note = "router_limit"  # the router cannot avoid areas this large
        else:
            try:
                detour = await router.route(
                    start, end, costing, exclude=[circle(h.lat, h.lng, h.zone_km) for h in hazards]
                )
            except RoutingError:
                note = "no_detour"  # e.g. the destination is inside a zone
            else:
                route, avoided = detour, True
                hazards = await event_hazards(session, route["coordinates"])
    return {
        "coordinates": route["coordinates"],
        "length_km": route["length_km"],
        "time_s": route["time_s"],
        "hazards": hazards,
        "fires_near_route": await fires_near(session, route["coordinates"]),
        "avoided": avoided,
        "avoidance_note": note,
    }
