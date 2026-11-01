"""Damage assessments: sync into geo_layers and read per event (TEST_DATABASE_URL)."""

import os
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

import src.services.damage as damage_mod
from src.db.database import get_db
from src.main import app
from src.models.event import DataSource, EventSource, EventType, GeoLayer, SeverityLevel
from src.repositories.event_repository import EventRepository
from src.services.copernicus_service import DamageAssessment

DB_URL = os.getenv("TEST_DATABASE_URL", "").replace("postgresql://", "postgresql+asyncpg://", 1)
pytestmark = pytest.mark.skipif(not DB_URL, reason="TEST_DATABASE_URL not set")

POINT = {"type": "Point", "coordinates": [91.9, 24.9]}
POLY = {"type": "Polygon", "coordinates": [[[91.8, 24.8], [92.0, 24.8], [92.0, 25.0], [91.8, 24.8]]]}


class FakeCopernicus:
    def __init__(self):
        self.calls = []

    async def fetch_damage_assessments(self, code):
        self.calls.append(code)
        ts = datetime(2026, 10, 2, tzinfo=UTC)
        return [
            DamageAssessment(code, "1", "Old town", "GRA", POLY, "Destroyed", 1.2, ts, "https://emergency.copernicus.eu/a.pdf"),
            DamageAssessment(code, "2", "Harbour", "GRA", POINT, "Possibly damaged", 0.4, ts, None),
        ]


@pytest.fixture
async def setup(monkeypatch):
    monkeypatch.setattr(damage_mod, "REQUEST_GAP_SECONDS", 0)
    engine = create_async_engine(DB_URL, poolclass=NullPool)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as s:
        await s.execute(text("TRUNCATE events, event_sources, data_sources, geo_layers CASCADE"))
        event = await EventRepository(s).create(
            type=EventType.flood, title="Flood", severity=SeverityLevel.high,
            start_date=datetime(2026, 10, 1, tzinfo=UTC), is_active=True, lat=24.9, lng=91.9,
        )
        src = DataSource(name="Copernicus", type="api")
        s.add(src)
        await s.flush()
        s.add(EventSource(event_id=event.id, source_id=src.id, external_id="EMSR900"))
        await s.commit()

    async def override():
        async with maker() as session:
            yield session

    app.dependency_overrides[get_db] = override
    yield maker, event.id
    app.dependency_overrides.pop(get_db, None)
    await engine.dispose()


async def test_sync_replaces_and_endpoint_summarises(setup):
    maker, event_id = setup
    fake = FakeCopernicus()
    for _ in range(2):  # a second run replaces, never duplicates
        async with maker() as s:
            result = await damage_mod.sync_damage(s, fake)
            await s.commit()
    assert result == {"events": 1, "assessments": 2}
    assert fake.calls == ["EMSR900", "EMSR900"]
    async with maker() as s:
        assert await s.scalar(select(func.count()).select_from(GeoLayer)) == 2

    with TestClient(app) as c:
        body = c.get(f"/api/v1/events/{event_id}/damage").json()
        assert body["total"] == 2
        assert body["by_grade"]["destroyed"] == 1
        assert body["areas"][0]["grade"] == "destroyed"
        assert body["areas"][0]["geometry"]["type"] == "Polygon"
        assert body["activations"] == ["EMSR900"]
        assert c.get(f"/api/v1/events/{uuid4()}/damage").status_code == 404
