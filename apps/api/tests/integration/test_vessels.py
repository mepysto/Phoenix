"""AIS vessel stream → PostGIS → map endpoint, with a fake socket (TEST_DATABASE_URL)."""

import json
import os
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from src.core.config import get_settings
from src.db.database import get_db
from src.main import app
from src.models.event import EventType, SeverityLevel
from src.models.vessel import VesselPosition
from src.repositories.event_repository import EventRepository
from src.services.tracks.vessels import VesselStream, VesselUpdate, store

DB_URL = os.getenv("TEST_DATABASE_URL", "").replace("postgresql://", "postgresql+asyncpg://", 1)
pytestmark = pytest.mark.skipif(not DB_URL, reason="TEST_DATABASE_URL not set")


def report(mmsi, lat, lng, name=None):
    return json.dumps({
        "MessageType": "PositionReport",
        "MetaData": {"MMSI": mmsi, "ShipName": name or ""},
        "Message": {"PositionReport": {"UserID": mmsi, "Latitude": lat, "Longitude": lng, "Sog": 10,
                                        "Cog": 45, "TrueHeading": 40, "Valid": True}},
    })


class FakeSocket:
    def __init__(self, messages):
        self.messages = list(messages)
        self.sent = []

    async def send(self, message):
        self.sent.append(json.loads(message))

    async def recv(self):
        if not self.messages:
            raise ConnectionError("stream closed")
        return self.messages.pop(0)


@pytest.fixture
async def maker():
    engine = create_async_engine(DB_URL, poolclass=NullPool)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as s:
        await s.execute(text("TRUNCATE events, event_sources, data_sources, vessel_positions CASCADE"))
        repo = EventRepository(s)
        await repo.create(type=EventType.hurricane, title="Typhoon near Tokyo", severity=SeverityLevel.critical,
                          lat=35.0, lng=139.5, start_date=datetime(2026, 9, 23, tzinfo=UTC), is_active=True)
        await repo.create(type=EventType.flood, title="Minor flood", severity=SeverityLevel.low,
                          lat=10.0, lng=10.0, start_date=datetime(2026, 9, 23, tzinfo=UTC), is_active=True)
        await s.commit()
    yield maker
    await engine.dispose()


@pytest.mark.asyncio
async def test_stream_subscribes_near_severe_events_and_stores_ships(maker):
    socket = FakeSocket([
        report(431000001, 35.2, 139.6, "RELIEF ONE"),
        report(431000002, 34.9, 139.9),
        report(431000001, 35.3, 139.7),  # newer position, name kept from the first report
    ])

    @asynccontextmanager
    async def connect():
        yield socket

    stream = VesselStream("test-key", maker, connect, max_boxes=20, box_degrees=3)
    with pytest.raises(ConnectionError):
        await stream.run_once()
    await stream.flush()  # run_forever flushes after a dropped connection

    subscription = socket.sent[0]
    assert subscription["APIKey"] == "test-key"
    assert subscription["BoundingBoxes"] == [[[32.0, 136.5], [38.0, 142.5]]]  # only the critical event
    async with maker() as s:
        ships = {v.mmsi: v for v in (await s.execute(select(VesselPosition))).scalars()}
    assert set(ships) == {431000001, 431000002}
    assert (ships[431000001].latitude, ships[431000001].name) == (35.3, "RELIEF ONE")


@pytest.mark.asyncio
async def test_store_prunes_old_positions(maker):
    now = datetime.now(UTC)
    async with maker() as s:
        await store(s, [VesselUpdate(mmsi=431000003, latitude=1.0, longitude=1.0, at=now - timedelta(hours=3))], now - timedelta(hours=3))
        await store(s, [VesselUpdate(mmsi=431000004, latitude=2.0, longitude=2.0, at=now)], now)
        assert [v.mmsi for v in (await s.execute(select(VesselPosition))).scalars()] == [431000004]


@pytest.mark.asyncio
async def test_endpoint_serves_recent_ships_in_view(maker, monkeypatch):
    now = datetime.now(UTC)
    async with maker() as s:
        await store(s, [
            VesselUpdate(mmsi=431000005, latitude=35.1, longitude=139.8, name="IN VIEW", at=now),
            VesselUpdate(mmsi=431000006, latitude=35.1, longitude=139.8, at=now - timedelta(hours=1)),  # too old
            VesselUpdate(mmsi=431000007, latitude=-10.0, longitude=20.0, at=now),  # outside
        ], now)

    async def override_db():
        async with maker() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    try:
        client = TestClient(app)
        params = {"min_lng": 130, "min_lat": 30, "max_lng": 145, "max_lat": 40}
        monkeypatch.setattr(get_settings(), "aisstream_api_key", None)
        body = client.get("/api/v1/tracks/vessels", params=params).json()
        assert body["enabled"] is False
        assert [f["properties"]["name"] for f in body["features"]] == ["IN VIEW"]
        monkeypatch.setattr(get_settings(), "aisstream_api_key", SecretStr("x"))
        assert client.get("/api/v1/tracks/vessels", params=params).json()["enabled"] is True
    finally:
        app.dependency_overrides.pop(get_db, None)
