"""Spatial filters against PostGIS (TEST_DATABASE_URL, disposable database)."""

import os
from datetime import UTC, datetime

import pytest
from sqlalchemy import select, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.models.event import Event, EventType, SeverityLevel
from src.repositories.event_repository import EventRepository, event_filter_conditions
from src.schemas.event import EventFilter

DB_URL = os.getenv("TEST_DATABASE_URL", "").replace("postgresql://", "postgresql+asyncpg://", 1)
pytestmark = pytest.mark.skipif(not DB_URL, reason="TEST_DATABASE_URL not set")

POINTS = {"fiji": (-17.7, 178.0), "samoa": (-13.8, -172.0), "tokyo": (35.7, 139.7)}


@pytest.fixture
async def session():
    engine = create_async_engine(DB_URL)
    async with async_sessionmaker(engine, expire_on_commit=False)() as s:
        await s.execute(text("TRUNCATE events, event_sources, data_sources CASCADE"))
        repo = EventRepository(s)
        for name, (lat, lng) in POINTS.items():
            await repo.create(
                type=EventType.earthquake, title=name, severity=SeverityLevel.low,
                start_date=datetime(2026, 9, 1, tzinfo=UTC), lat=lat, lng=lng,
            )
        yield s
        await s.rollback()
    await engine.dispose()


async def _titles(session, **filters) -> list[str]:
    events, _ = await EventRepository(session).list_events(EventFilter(**filters), 50, 0)
    return sorted(e.title for e in events)


@pytest.mark.asyncio
async def test_bbox_crossing_antimeridian_returns_both_sides(session):
    # Pacific view from 170E to 170W: min_lng > max_lng
    titles = await _titles(session, min_lng=170, min_lat=-30, max_lng=-170, max_lat=0)
    assert titles == ["fiji", "samoa"]


@pytest.mark.asyncio
async def test_regular_bbox(session):
    assert await _titles(session, min_lng=120, min_lat=20, max_lng=150, max_lat=50) == ["tokyo"]


@pytest.mark.asyncio
async def test_radius_search_uses_geography_index(session):
    await session.execute(text("SET LOCAL enable_seqscan = off"))
    stmt = select(Event.id).where(
        *event_filter_conditions(EventFilter(center_lat=35.0, center_lng=139.0, radius_km=200))
    )
    sql = str(stmt.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))
    plan = "\n".join((await session.execute(text("EXPLAIN " + sql))).scalars().all())
    assert "idx_events_location_geog" in plan, plan
    assert await _titles(session, center_lat=35.0, center_lng=139.0, radius_km=200) == ["tokyo"]
