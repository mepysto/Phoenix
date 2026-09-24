"""Free-text event search against PostgreSQL (TEST_DATABASE_URL, disposable DB)."""

import os
from datetime import UTC, datetime

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.models.event import EventType, SeverityLevel
from src.repositories.event_repository import EventRepository
from src.schemas.event import EventFilter

DB_URL = os.getenv("TEST_DATABASE_URL", "").replace("postgresql://", "postgresql+asyncpg://", 1)
pytestmark = pytest.mark.skipif(not DB_URL, reason="TEST_DATABASE_URL not set")


@pytest.fixture
async def repo():
    engine = create_async_engine(DB_URL)
    async with async_sessionmaker(engine, expire_on_commit=False)() as session:
        await session.execute(text("TRUNCATE events, event_sources, data_sources CASCADE"))
        repository = EventRepository(session)
        for title, region in [
            ("Flood in Valencia", "Spain"),
            ("M 6.1 Earthquake", "Japan"),
            ("100% cropland burned", "Chad"),
        ]:
            await repository.create(
                type=EventType.other, title=title, region=region,
                severity=SeverityLevel.low, start_date=datetime(2026, 9, 1, tzinfo=UTC),
            )
        yield repository
        await session.rollback()
    await engine.dispose()


async def _titles(repo: EventRepository, q: str) -> list[str]:
    events, _ = await repo.list_events(EventFilter(q=q), limit=50, offset=0)
    return sorted(e.title for e in events)


@pytest.mark.asyncio
async def test_search_matches_title_and_region_case_insensitively(repo):
    assert await _titles(repo, "valencia") == ["Flood in Valencia"]
    assert await _titles(repo, "JAPAN") == ["M 6.1 Earthquake"]


@pytest.mark.asyncio
async def test_like_wildcards_are_literal(repo):
    assert await _titles(repo, "%") == ["100% cropland burned"]
    assert await _titles(repo, "_") == []
