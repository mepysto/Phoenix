"""Scheduler jobs must not run concurrently across workers (TEST_DATABASE_URL)."""

import os

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.services import scheduler as scheduler_module

DB_URL = os.getenv("TEST_DATABASE_URL", "").replace("postgresql://", "postgresql+asyncpg://", 1)
pytestmark = pytest.mark.skipif(not DB_URL, reason="TEST_DATABASE_URL not set")


@pytest.fixture
async def service(monkeypatch):
    engine = create_async_engine(DB_URL)
    # Each "worker" gets its own connection from this pool, like separate processes
    monkeypatch.setattr(
        scheduler_module, "async_session_maker", async_sessionmaker(engine, expire_on_commit=False)
    )
    yield scheduler_module.SchedulerService()
    await engine.dispose()


@pytest.mark.asyncio
async def test_second_worker_skips_while_first_holds_the_lock(service):
    async with service._exclusive_job("gdacs") as first:
        assert first is not None
        async with service._exclusive_job("gdacs") as second:
            assert second is None  # would have ingested the same feed twice
        # Different jobs are independent
        async with service._exclusive_job("usgs") as other:
            assert other is not None
            await other.commit()
        await first.commit()


@pytest.mark.asyncio
async def test_lock_is_released_on_commit_and_on_error(service):
    async with service._exclusive_job("eonet") as session:
        await session.commit()
    async with service._exclusive_job("eonet") as session:
        assert session is not None

    with pytest.raises(RuntimeError):
        async with service._exclusive_job("copernicus") as session:
            raise RuntimeError("job crashed mid-run")
    async with service._exclusive_job("copernicus") as session:
        assert session is not None  # rollback released it; no stale lock
