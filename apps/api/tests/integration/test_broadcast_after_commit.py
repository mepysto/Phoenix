"""WebSocket broadcasts must follow the database transaction outcome.

Requires TEST_DATABASE_URL pointing at a migrated, disposable database.
"""

import asyncio
import os
from datetime import UTC, datetime

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.services.broadcaster import event_broadcaster
from src.services.connectors.base import RawEvent
from src.services.ingestion_service import IngestionService

DB_URL = os.getenv("TEST_DATABASE_URL", "").replace("postgresql://", "postgresql+asyncpg://", 1)
pytestmark = pytest.mark.skipif(not DB_URL, reason="TEST_DATABASE_URL not set")


def _event(external_id: str, lat: float) -> RawEvent:
    return RawEvent(
        source_name="USGS",
        external_id=external_id,
        title=f"M 5.0 - {external_id}",
        start_date=datetime(2026, 9, 1, tzinfo=UTC),
        lat=lat,
        lng=10.0,
        event_type_raw="earthquake",
        magnitude=5.0,
    )


@pytest.fixture
async def session_factory():
    engine = create_async_engine(DB_URL)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        await s.execute(text("TRUNCATE events, event_sources, data_sources CASCADE"))
        await s.commit()
    yield factory
    await engine.dispose()


@pytest.fixture
def sent(monkeypatch) -> list[dict]:
    messages: list[dict] = []

    async def record(message: dict) -> None:
        messages.append(message)

    monkeypatch.setattr(event_broadcaster.manager, "broadcast", record)
    return messages


async def _drain() -> None:
    for _ in range(5):
        await asyncio.sleep(0)


@pytest.mark.asyncio
async def test_nothing_is_sent_before_commit_and_all_after(session_factory, sent):
    async with session_factory() as session:
        await IngestionService(session).ingest_usgs_events(
            [_event("a", 1.0), _event("b", 40.0)], atomic=False
        )
        await _drain()
        assert sent == []
        await session.commit()
    await _drain()
    assert len(sent) == 2


@pytest.mark.asyncio
async def test_rollback_discards_broadcasts(session_factory, sent):
    async with session_factory() as session:
        await IngestionService(session).ingest_usgs_events([_event("c", 1.0)], atomic=False)
        await session.rollback()
    await _drain()
    assert sent == []


@pytest.mark.asyncio
async def test_failed_event_does_not_drop_earlier_broadcasts(session_factory, sent, monkeypatch):
    async with session_factory() as session:
        service = IngestionService(session)
        original = service.event_source_repo.upsert
        calls = {"n": 0}

        async def flaky_upsert(**kwargs):
            calls["n"] += 1
            if calls["n"] == 2:
                raise RuntimeError("simulated failure on second event")
            return await original(**kwargs)

        monkeypatch.setattr(service.event_source_repo, "upsert", flaky_upsert)
        result = await service.ingest_usgs_events(
            [_event("d", 1.0), _event("e", 40.0), _event("f", -40.0)], atomic=False
        )
        await session.commit()
    await _drain()

    assert result["created"] == 2 and result["failed"] == 1
    # The failed event's savepoint was rolled back: only survivors are announced
    assert sorted(m["data"]["title"] for m in sent) == ["M 5.0 - d", "M 5.0 - f"]
