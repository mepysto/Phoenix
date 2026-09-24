"""Conflict-zone policy applied by the aircraft endpoint, zones from PostGIS events."""

import os
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from src.core.config import get_settings
from src.db.database import get_db
from src.api.v1 import tracks as tracks_api
from src.main import app
from src.models.event import EventType, SeverityLevel
from src.repositories.event_repository import EventRepository
from src.services.tracks import aircraft as aircraft_module
from src.services.tracks import conflict_policy

DB_URL = os.getenv("TEST_DATABASE_URL", "").replace("postgresql://", "postgresql+asyncpg://", 1)
pytestmark = pytest.mark.skipif(not DB_URL, reason="TEST_DATABASE_URL not set")


def plane(lat, lng, military):
    return {"type": "Feature", "geometry": {"type": "Point", "coordinates": [lng, lat]},
            "properties": {"hex": "x", "callsign": "C", "military": military}}


@pytest.fixture
async def client(monkeypatch):
    engine = create_async_engine(DB_URL, poolclass=NullPool)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as s:
        await s.execute(text("TRUNCATE events, event_sources, data_sources CASCADE"))
        await EventRepository(s).create(type=EventType.war, title="Front line", severity=SeverityLevel.high,
                                        lat=48.5, lng=35.0, start_date=datetime(2026, 9, 1, tzinfo=UTC), is_active=True)
        await s.commit()

    async def override_db():
        async with maker() as session:
            yield session

    async def fake_around(lat, lng, radius_nm):
        return {"type": "FeatureCollection", "stale": False,
                "features": [plane(48.6, 35.2, True), plane(48.6, 35.2, False), plane(40.0, 20.0, True)]}

    monkeypatch.setattr(aircraft_module.aircraft_service, "around", fake_around)
    # Fresh zones per test (the cache keeps zones for 5 minutes)
    monkeypatch.setattr(tracks_api, "conflict_zone_cache", conflict_policy.ConflictZoneCache())
    app.dependency_overrides[get_db] = override_db
    yield TestClient(app)
    app.dependency_overrides.pop(get_db, None)
    await engine.dispose()


def test_grid_policy_generalises_military_near_conflict(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "conflict_zone_policy", "grid")
    features = client.get("/api/v1/tracks/aircraft", params={"lat": 48, "lng": 35}).json()["features"]
    assert features[0]["properties"] == {"military": True, "generalised": True}
    assert features[1]["properties"]["callsign"] == "C"  # civil aircraft untouched
    assert features[2]["properties"]["callsign"] == "C"  # military far from any conflict


def test_policy_off_by_default(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "conflict_zone_policy", "off")
    features = client.get("/api/v1/tracks/aircraft", params={"lat": 48, "lng": 35}).json()["features"]
    assert all(f["properties"].get("callsign") == "C" for f in features)
