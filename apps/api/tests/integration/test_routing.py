"""Hazard-aware routing against PostGIS with a fake router (TEST_DATABASE_URL)."""

import os
from datetime import UTC, datetime

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from src.models.event import EventType, SeverityLevel
from src.repositories.event_repository import EventRepository
from src.services.hazards.firms import Detection, store_detections
from src.services.routing import RoutingError, circumference_m, decode_polyline6, plan_route

DB_URL = os.getenv("TEST_DATABASE_URL", "").replace("postgresql://", "postgresql+asyncpg://", 1)
pytestmark = pytest.mark.skipif(not DB_URL, reason="TEST_DATABASE_URL not set")

# Straight west-east route along latitude 35.0 from lng 139.0 to 140.0
DIRECT = [(139.0 + i * 0.1, 35.0) for i in range(11)]
# Detour bowing north to latitude 35.5
DETOUR = [(139.0, 35.0), (139.2, 35.5), (139.8, 35.5), (140.0, 35.0)]


class FakeRouter:
    def __init__(self, detour_possible=True):
        self.calls = []
        self.detour_possible = detour_possible

    async def route(self, start, end, costing, exclude=None):
        self.calls.append(exclude)
        if exclude and not self.detour_possible:
            raise RoutingError("No path could be found for input", no_route=True)
        coords = DETOUR if exclude else DIRECT
        return {"coordinates": coords, "length_km": 90.0 if not exclude else 120.0, "time_s": 3600}


@pytest.fixture
async def session():
    engine = create_async_engine(DB_URL, poolclass=NullPool)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as s:
        await s.execute(text("TRUNCATE events, event_sources, data_sources, fire_detections CASCADE"))
        repo = EventRepository(s)
        start = datetime(2026, 9, 23, tzinfo=UTC)
        # On the direct route: a high-severity flood (10 km zone)
        await repo.create(type=EventType.flood, title="Flood on the route", severity=SeverityLevel.high,
                          lat=35.02, lng=139.5, start_date=start, is_active=True)
        # Low severity: ignored even though it is on the route
        await repo.create(type=EventType.storm, title="Minor storm", severity=SeverityLevel.low,
                          lat=35.0, lng=139.3, start_date=start, is_active=True)
        # Critical but far away (60 km north of the route, beyond its 25 km zone)
        await repo.create(type=EventType.earthquake, title="Far quake", severity=SeverityLevel.critical,
                          lat=35.55 + 0.5, lng=139.5, start_date=start, is_active=True)
        await store_detections(s, [
            Detection("N", "VIIRS", datetime.now(UTC), 35.005, 139.71, 20.0, 330.0, "n", "D"),  # 0.5 km off route
            Detection("N", "VIIRS", datetime.now(UTC), 36.0, 139.71, 20.0, 330.0, "n", "D"),  # far
        ])
        await s.commit()
        yield s
    await engine.dispose()


@pytest.mark.asyncio
async def test_hazards_along_the_route_without_avoidance(session):
    plan = await plan_route(session, FakeRouter(), (35.0, 139.0), (35.0, 140.0), "auto", False, 10_000)
    assert [h.title for h in plan["hazards"]] == ["Flood on the route"]
    assert plan["hazards"][0].zone_km == 10 and plan["hazards"][0].distance_km < 3
    assert plan["fires_near_route"] == 1
    assert (plan["avoided"], plan["avoidance_note"]) == (False, None)


@pytest.mark.asyncio
async def test_public_router_limit_is_reported(session):
    router = FakeRouter()
    plan = await plan_route(session, router, (35.0, 139.0), (35.0, 140.0), "auto", True, 10_000)
    assert circumference_m(10) > 10_000
    assert plan["avoidance_note"] == "router_limit" and plan["avoided"] is False
    assert router.calls == [None]  # no pointless second request


@pytest.mark.asyncio
async def test_detour_when_the_router_allows_large_areas(session):
    router = FakeRouter()
    plan = await plan_route(session, router, (35.0, 139.0), (35.0, 140.0), "auto", True, 1_000_000)
    assert plan["avoided"] is True
    assert plan["coordinates"] == DETOUR
    assert plan["hazards"] == []  # the detour clears the flood zone
    assert plan["fires_near_route"] == 0
    exclude = router.calls[1]
    assert len(exclude) == 1 and exclude[0][0] == exclude[0][-1]  # one closed ring around the flood


@pytest.mark.asyncio
async def test_no_detour_keeps_the_route_with_a_warning(session):
    plan = await plan_route(session, FakeRouter(detour_possible=False), (35.0, 139.0), (35.0, 140.0), "auto", True, 1_000_000)
    assert plan["avoidance_note"] == "no_detour" and plan["coordinates"] == DIRECT
    assert [h.title for h in plan["hazards"]] == ["Flood on the route"]


def test_decode_polyline6():
    def encode(coords):
        out, prev = [], (0, 0)
        for lng, lat in coords:
            point = (round(lat * 1e6), round(lng * 1e6))
            for value, last in zip(point, prev, strict=True):
                delta = value - last
                delta = ~(delta << 1) if delta < 0 else delta << 1
                while delta >= 0x20:
                    out.append(chr((0x20 | (delta & 0x1F)) + 63))
                    delta >>= 5
                out.append(chr(delta + 63))
            prev = point
        return "".join(out)

    coords = [(139.75998, 35.680004), (139.639882, 35.449836), (-122.27291, 37.82539)]
    decoded = decode_polyline6(encode(coords))
    assert decoded == pytest.approx(coords)
