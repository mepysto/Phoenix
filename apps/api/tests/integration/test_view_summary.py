"""Map view summary and nearby events against PostGIS (TEST_DATABASE_URL)."""

import os
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from src.db.database import get_db
from src.main import app
from src.models.event import EventType, SeverityLevel
from src.repositories.event_repository import EventRepository

DB_URL = os.getenv("TEST_DATABASE_URL", "").replace("postgresql://", "postgresql+asyncpg://", 1)
pytestmark = pytest.mark.skipif(not DB_URL, reason="TEST_DATABASE_URL not set")

SUMMARY = "/api/v1/geodata/summary"
NEARBY = "/api/v1/geodata/nearby"


@pytest.fixture
async def client():
    engine = create_async_engine(DB_URL, poolclass=NullPool)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as s:
        await s.execute(text("TRUNCATE events, event_sources, data_sources CASCADE"))
        repo = EventRepository(s)
        for title, kind, severity, lat, lng, population, end in [
            # Tokyo area
            ("tokyo quake", EventType.earthquake, SeverityLevel.high, 35.7, 139.7, 1000, None),
            ("yokohama flood", EventType.flood, SeverityLevel.medium, 35.4, 139.6, 500, None),
            ("chiba fire (ended)", EventType.wildfire, SeverityLevel.low, 35.6, 140.1, 9, datetime(2026, 9, 2, tzinfo=UTC)),
            # Fiji, just west of the antimeridian
            ("fiji cyclone", EventType.hurricane, SeverityLevel.critical, -17.7, 178.0, None, None),
            # Far away
            ("lima quake", EventType.earthquake, SeverityLevel.medium, -12.0, -77.0, 20, None),
        ]:
            await repo.create(
                type=kind, title=title, severity=severity, lat=lat, lng=lng,
                affected_population=population, start_date=datetime(2026, 9, 1, tzinfo=UTC),
                end_date=end, is_active=end is None,
            )
        await s.commit()

    async def override():
        async with maker() as session:
            yield session

    app.dependency_overrides[get_db] = override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.pop(get_db, None)
    await engine.dispose()


def test_summary_counts_active_events_in_view(client):
    japan = {"min_lng": 130, "min_lat": 30, "max_lng": 145, "max_lat": 40}
    body = client.get(SUMMARY, params=japan).json()
    assert body["total"] == 2  # the ended fire is excluded
    assert body["by_severity"] == {"high": 1, "medium": 1}
    assert body["by_type"] == {"earthquake": 1, "flood": 1}
    assert body["affected_population"] == 1500
    assert body["last_updated"] is not None


def test_summary_whole_world_filters_and_antimeridian(client):
    assert client.get(SUMMARY).json()["total"] == 4
    assert client.get(SUMMARY, params={"types": "earthquake"}).json()["total"] == 2
    # Pacific view crossing the antimeridian (west > east) still finds Fiji
    pacific = client.get(SUMMARY, params={"min_lng": 170, "min_lat": -30, "max_lng": -170, "max_lat": 0}).json()
    assert pacific["by_type"] == {"hurricane": 1}
    assert pacific["affected_population"] == 0


def test_summary_at_instant_includes_events_ended_later(client):
    body = client.get(SUMMARY, params={"at": "2026-09-01T12:00:00Z"}).json()
    assert body["total"] == 5


def test_nearby_orders_by_distance(client):
    body = client.get(NEARBY, params={"lat": 35.68, "lng": 139.76, "radius_km": 200}).json()
    titles = [item["event"]["title"] for item in body["data"]]
    assert titles == ["tokyo quake", "yokohama flood"]
    assert body["data"][0]["distance_km"] < body["data"][1]["distance_km"] < 60
    assert body["radius_km"] == 200


def test_nearby_validates_input(client):
    assert client.get(NEARBY, params={"lat": 91, "lng": 0}).status_code == 422
    assert client.get(NEARBY, params={"lat": 0, "lng": 0, "radius_km": 0}).status_code == 422
    assert client.get(NEARBY, params={"lat": 0, "lng": 0, "limit": 51}).status_code == 422
