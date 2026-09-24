"""Timeline histogram and point-in-time filter against PostGIS (TEST_DATABASE_URL)."""

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


def d(day: int, hour: int = 0) -> datetime:
    return datetime(2026, 9, day, hour, tzinfo=UTC)


@pytest.fixture
async def client():
    engine = create_async_engine(DB_URL, poolclass=NullPool)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as s:
        await s.execute(text("TRUNCATE events, event_sources, data_sources CASCADE"))
        repo = EventRepository(s)
        for title, kind, start, end in [
            ("quake 1", EventType.earthquake, d(1, 3), d(1, 5)),
            ("quake 2", EventType.earthquake, d(1, 20), None),
            ("flood", EventType.flood, d(1, 12), d(4)),
            ("fire", EventType.wildfire, d(3), None),
        ]:
            await repo.create(type=kind, title=title, severity=SeverityLevel.medium,
                              start_date=start, end_date=end, is_active=end is None, lat=1.0, lng=1.0)
        await s.commit()

    async def override():
        async with maker() as session:
            yield session

    app.dependency_overrides[get_db] = override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.pop(get_db, None)
    await engine.dispose()


def titles(client, **params) -> list[str]:
    body = client.get("/api/v1/events", params=params).json()
    return sorted(e["title"] for e in body["data"])


def test_at_returns_only_events_ongoing_at_that_instant(client) -> None:
    assert titles(client, at="2026-09-01T04:00:00Z") == ["quake 1"]
    assert titles(client, at="2026-09-02T00:00:00Z") == ["flood", "quake 2"]  # quake 1 ended
    assert titles(client, at="2026-09-05T00:00:00Z") == ["fire", "quake 2"]  # flood ended day 4


def test_daily_histogram_counts_onsets_by_type(client) -> None:
    body = client.get(
        "/api/v1/events/timeline",
        params={"start": "2026-09-01T00:00:00Z", "end": "2026-09-05T00:00:00Z"},
    ).json()
    buckets = {b["start"][:10]: b for b in body["buckets"]}
    assert buckets["2026-09-01"]["total"] == 3
    assert buckets["2026-09-01"]["by_type"] == {"earthquake": 2, "flood": 1}
    assert buckets["2026-09-03"]["by_type"] == {"wildfire": 1}
    assert "2026-09-02" not in buckets  # empty days are omitted


def test_timeline_filters_and_validation(client) -> None:
    body = client.get(
        "/api/v1/events/timeline",
        params={"start": "2026-09-01T00:00:00Z", "end": "2026-09-05T00:00:00Z", "types": ["flood"]},
    ).json()
    assert [b["total"] for b in body["buckets"]] == [1]
    bad = client.get("/api/v1/events/timeline", params={"start": "2026-09-05T00:00:00Z", "end": "2026-09-01T00:00:00Z"})
    assert bad.status_code == 422
    too_long = client.get(
        "/api/v1/events/timeline",
        params={"start": "2020-01-01T00:00:00Z", "end": "2026-01-01T00:00:00Z", "bucket": "hour"},
    )
    assert too_long.status_code == 422
