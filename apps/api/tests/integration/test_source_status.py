"""Sync failures are persisted and surface as 'failing' (TEST_DATABASE_URL)."""

import os
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.api.v1.sources import source_health
from src.core.exceptions import ExternalAPIError
from src.repositories.data_source_repository import DataSourceRepository
from src.services import scheduler as scheduler_module

DB_URL = os.getenv("TEST_DATABASE_URL", "").replace("postgresql://", "postgresql+asyncpg://", 1)
pytestmark = pytest.mark.skipif(not DB_URL, reason="TEST_DATABASE_URL not set")


@pytest.fixture
async def factory(monkeypatch):
    engine = create_async_engine(DB_URL)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(scheduler_module, "async_session_maker", maker)
    async with maker() as s:
        await s.execute(text("TRUNCATE events, event_sources, data_sources CASCADE"))
        await s.commit()
    yield maker
    await engine.dispose()


@pytest.mark.asyncio
async def test_failure_keeps_last_success_and_marks_failing(factory):
    last_success = datetime.now(UTC) - timedelta(minutes=3)
    async with factory() as s:
        repo = DataSourceRepository(s)
        source = await repo.get_or_create(name="USGS", type="disaster_alert", defaults={})
        await repo.update_sync_status(source.id, last_sync=last_success, status="success")
        await s.commit()

    service = scheduler_module.SchedulerService()
    await service._record_failure("USGS", ExternalAPIError("timed out", service_name="USGS"))
    await service._record_failure("USGS", ExternalAPIError("timed out", service_name="USGS"))

    async with factory() as s:
        source = await DataSourceRepository(s).get_by_name("USGS")
    assert source.last_sync == last_success  # not overwritten by the failure
    assert source.consecutive_failures == 2
    assert source.last_sync_error == "ExternalAPIError"  # no internal message
    assert source_health(source, datetime.now(UTC)) == "failing"


@pytest.mark.asyncio
async def test_failure_for_unknown_source_is_ignored(factory):
    # First-ever sync failed before the source row existed: nothing to mark
    await scheduler_module.SchedulerService()._record_failure("NEW", RuntimeError("x"))
    async with factory() as s:
        assert await DataSourceRepository(s).get_by_name("NEW") is None
