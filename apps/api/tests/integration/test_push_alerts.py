"""Closed-tab alerts: subscribe, match, deliver once, clean up (TEST_DATABASE_URL)."""

import json
import os
from datetime import UTC, datetime, timedelta

import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from src.core.config import get_settings
from src.db.database import get_db
from src.main import app
from src.models.event import EventType, SeverityLevel
from src.models.push import PushSubscription
from src.repositories.event_repository import EventRepository
from src.services.push.alerts import dispatch, is_push_endpoint
from src.services.push.webpush import VapidKeys, b64u_encode, public_bytes
from tests.services.test_webpush import decrypt

DB_URL = os.getenv("TEST_DATABASE_URL", "").replace("postgresql://", "postgresql+asyncpg://", 1)
pytestmark = pytest.mark.skipif(not DB_URL, reason="TEST_DATABASE_URL not set")

KEYS = VapidKeys.generate()
ENDPOINT = "https://fcm.googleapis.com/fcm/send/abc123"


class FakePushService:
    def __init__(self, status=201):
        self.status = status
        self.sent = []

    async def post(self, url, *, headers, content):
        self.sent.append((url, headers, content))

        class R:
            status_code = self.status

        return R()


@pytest.fixture
async def env():
    engine = create_async_engine(DB_URL, poolclass=NullPool)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as s:
        await s.execute(text("TRUNCATE push_deliveries, push_subscriptions, events, event_sources, data_sources CASCADE"))
        await s.commit()

    async def override():
        async with maker() as session:
            yield session
            await session.commit()

    settings = get_settings().model_copy(update={"vapid_private_key": SecretStr(KEYS.private_b64u)})
    app.dependency_overrides[get_db] = override
    app.dependency_overrides[get_settings] = lambda: settings
    yield maker
    app.dependency_overrides.clear()
    await engine.dispose()


def test_endpoint_allowlist():
    assert is_push_endpoint(ENDPOINT)
    assert is_push_endpoint("https://updates.push.services.mozilla.com/wpush/v2/x")
    assert is_push_endpoint("https://web.push.apple.com/abc")
    for bad in [
        "http://fcm.googleapis.com/x",
        "https://evil.example/x",
        "https://fcm.googleapis.com.evil.example/x",
        "https://user@fcm.googleapis.com/x",
        "https://fcm.googleapis.com:8443/x",
        "https://169.254.169.254/latest",
    ]:
        assert not is_push_endpoint(bad), bad


async def test_subscribe_match_deliver_once(env):
    maker = env
    browser = ec.generate_private_key(ec.SECP256R1())
    auth = os.urandom(16)
    client = TestClient(app)
    sub = {
        "endpoint": ENDPOINT,
        "keys": {"p256dh": b64u_encode(public_bytes(browser.public_key())), "auth": b64u_encode(auth)},
        "areas": [{"name": "Sylhet", "lat": 24.8949, "lng": 91.8687, "radius_km": 100, "min_severity": "high"}],
    }
    assert client.get("/api/v1/push/vapid-public-key").json()["public_key"] == KEYS.public_b64u
    assert client.put("/api/v1/push/subscription", json={**sub, "endpoint": "https://evil.example/x"}).status_code == 422
    assert client.put("/api/v1/push/subscription", json=sub).status_code == 204
    async with maker() as s:
        stored = await s.scalar(select(PushSubscription))
        assert stored.areas[0]["lat"] == 24.9  # rounded to ~10 km

    now = datetime.now(UTC) + timedelta(seconds=5)
    async with maker() as s:
        repo = EventRepository(s)
        await repo.create(type=EventType.flood, title="Flood near Sylhet", severity=SeverityLevel.critical,
                          start_date=now, is_active=True, lat=24.95, lng=91.9, created_at=now)
        await repo.create(type=EventType.flood, title="Minor flood", severity=SeverityLevel.low,
                          start_date=now, is_active=True, lat=24.95, lng=91.9, created_at=now)
        await repo.create(type=EventType.earthquake, title="Far away", severity=SeverityLevel.critical,
                          start_date=now, is_active=True, lat=35.0, lng=139.0, created_at=now)
        await s.commit()

    push = FakePushService()
    for _ in range(2):  # the second run must not resend
        async with maker() as s:
            result = await dispatch(s, KEYS, "mailto:ops@phoenix.test", push, now=now + timedelta(minutes=1))
            await s.commit()
    assert len(push.sent) == 1
    url, headers, body = push.sent[0]
    assert url == ENDPOINT and headers["Content-Encoding"] == "aes128gcm"
    payload = json.loads(decrypt(body, browser, auth))
    assert payload["title"] == "Flood near Sylhet"
    assert payload["url"].startswith("/events/")
    assert result["sent"] == 0

    # A push service saying "gone" removes the subscription
    async with maker() as s:
        await EventRepository(s).create(type=EventType.flood, title="Another", severity=SeverityLevel.high,
                                        start_date=now, is_active=True, lat=24.9, lng=91.9, created_at=now)
        await s.commit()
    async with maker() as s:
        await dispatch(s, KEYS, "mailto:ops@phoenix.test", FakePushService(status=410), now=now + timedelta(minutes=2))
        await s.commit()
        assert await s.scalar(select(func.count()).select_from(PushSubscription)) == 0


def test_unsubscribe_and_unconfigured(env):
    client = TestClient(app)
    assert client.post("/api/v1/push/unsubscribe", json={"endpoint": ENDPOINT}).status_code == 204
    app.dependency_overrides[get_settings] = lambda: get_settings().model_copy(update={"vapid_private_key": None})
    assert client.get("/api/v1/push/vapid-public-key").status_code == 503
