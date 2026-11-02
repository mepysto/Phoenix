"""Spatial filters against PostGIS (TEST_DATABASE_URL, disposable database)."""

import os
from datetime import UTC, datetime

import pytest
from sqlalchemy import select, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.models.event import Event, EventType, SeverityLevel
from src.repositories.event_repository import EventRepository
from src.schemas.event import EventFilter
from src.utils.geo import point_within_distance

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
    # The radius predicate alone: with the canonical filter too, a near-empty
    # table lets the planner pick idx_events_is_canonical depending on stats
    radius = point_within_distance(Event.location, 35.0, 139.0, 200_000)
    stmt = select(Event.id).where(radius)
    sql = str(stmt.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))
    plan = "\n".join((await session.execute(text("EXPLAIN " + sql))).scalars().all())
    assert "idx_events_location_geog" in plan, plan
    assert await _titles(session, center_lat=35.0, center_lng=139.0, radius_km=200) == ["tokyo"]


@pytest.mark.asyncio
async def test_duplicate_candidates_need_same_type_place_and_time(session):
    repo = EventRepository(session)
    when = datetime(2026, 9, 1, tzinfo=UTC)
    # Near Tokyo: one flood (other type), one earthquake a week later (outside the window)
    await repo.create(
        type=EventType.flood, title="tokyo-flood", severity=SeverityLevel.low,
        start_date=when, lat=35.6, lng=139.6,
    )
    await repo.create(
        type=EventType.earthquake, title="tokyo-later", severity=SeverityLevel.low,
        start_date=datetime(2026, 9, 8, tzinfo=UTC), lat=35.7, lng=139.7,
    )
    found = await repo.find_candidates_by_spatiotemporal(
        event_type=EventType.earthquake, lat=35.65, lng=139.65, start_date=when,
        radius_meters=50_000, window_hours=48,
    )
    assert [e.title for e in found] == ["tokyo"]
    # Radius is in metres on the sphere: ~1,100 km from Fiji to Samoa across the antimeridian
    far = await repo.find_candidates_by_spatiotemporal(
        event_type=EventType.earthquake, lat=-17.7, lng=178.0, start_date=when,
        radius_meters=1_200_000,
    )
    assert sorted(e.title for e in far) == ["fiji", "samoa"]


@pytest.mark.asyncio
async def test_clusters_group_by_geohash_and_keep_singles_apart(session):
    from src.services.clustering_service import ClusteringService

    repo = EventRepository(session)
    for i, (lat, lng) in enumerate([(35.60, 139.60), (35.65, 139.70)]):
        await repo.create(
            type=EventType.flood, title=f"kanto-{i}",
            severity=SeverityLevel.critical if i else SeverityLevel.low,
            start_date=datetime(2026, 9, 2, tzinfo=UTC), lat=lat, lng=lng,
        )
    result = await ClusteringService(session).get_clusters(zoom=5, filters=EventFilter())
    assert result.total_events == 5  # three fixture points + two floods
    [kanto] = [c for c in result.clusters if 35 < c.center_lat < 36]
    assert kanto.count == 3  # tokyo + both floods
    assert 139.6 <= kanto.center_lng <= 139.7
    assert kanto.max_severity == "critical"
    # Fiji and Samoa are far apart: shown individually, not merged
    assert sorted(e.title for e in result.unclustered) == ["fiji", "samoa"]
