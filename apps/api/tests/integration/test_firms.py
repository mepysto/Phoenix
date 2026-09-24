"""FIRMS storage and the fires endpoint against PostGIS (TEST_DATABASE_URL)."""

import os
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from src.db.database import get_db
from src.main import app
from src.services.hazards.firms import Detection, prune_old, store_detections

DB_URL = os.getenv("TEST_DATABASE_URL", "").replace("postgresql://", "postgresql+asyncpg://", 1)
pytestmark = pytest.mark.skipif(not DB_URL, reason="TEST_DATABASE_URL not set")

NOW = datetime.now(UTC).replace(microsecond=0)


def fire(lat: float, lng: float, frp: float, hours_ago: float, satellite: str = "N") -> Detection:
    return Detection(
        satellite=satellite, instrument="VIIRS", acquired_at=NOW - timedelta(hours=hours_ago),
        latitude=lat, longitude=lng, frp=frp, brightness_k=330.0, confidence="nominal", daynight="D",
    )


@pytest.fixture
async def maker():
    engine = create_async_engine(DB_URL, poolclass=NullPool)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        await s.execute(text("TRUNCATE fire_detections"))
        await s.commit()
    yield factory
    await engine.dispose()


@pytest.mark.asyncio
async def test_store_is_idempotent_and_prune_removes_expired(maker) -> None:
    batch = [fire(-8.5, 120.6, 12.5, 1), fire(-8.6, 120.7, 3.0, 2), fire(10, 10, 1, 60)]
    async with maker() as s:
        assert await store_detections(s, batch) == 3
        assert await store_detections(s, batch) == 0  # same rows again: nothing new
        assert await prune_old(s) == 1  # the 60 h old one
        await s.commit()
        assert (await s.execute(text("SELECT count(*) FROM fire_detections"))).scalar() == 2


@pytest.fixture
async def client(maker):
    async with maker() as s:
        await store_detections(s, [
            fire(-8.5, 120.6, 50.0, 1), fire(-8.6, 120.7, 5.0, 2),
            fire(-8.7, 120.8, 900.0, 30),  # older than the default 24 h window
            fire(-17.7, 178.0, 7.0, 1), fire(-13.8, -172.0, 8.0, 1),
        ])
        await s.commit()

    async def override():
        async with maker() as session:
            yield session

    app.dependency_overrides[get_db] = override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.pop(get_db, None)


def _fires(client, **params):
    return client.get("/api/v1/hazards/fires", params=params).json()


def test_viewport_strongest_first_within_time_window(client) -> None:
    body = _fires(client, min_lng=115, min_lat=-12, max_lng=125, max_lat=-5)
    assert [f["properties"]["frp"] for f in body["features"]] == [50.0, 5.0]
    wider = _fires(client, min_lng=115, min_lat=-12, max_lng=125, max_lat=-5, hours=48)
    assert wider["features"][0]["properties"]["frp"] == 900.0


def test_limit_truncates_and_antimeridian_split(client) -> None:
    assert _fires(client, min_lng=115, min_lat=-12, max_lng=125, max_lat=-5, limit=1)["truncated"] is True
    pacific = _fires(client, min_lng=170, min_lat=-30, max_lng=-170, max_lat=0)
    assert sorted(f["properties"]["frp"] for f in pacific["features"]) == [7.0, 8.0]
