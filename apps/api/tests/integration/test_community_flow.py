"""Sign-in, organisations, needs, offers, matching and two-sided connections
end to end against PostGIS (TEST_DATABASE_URL)."""

import os
import re
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from src.api.v1.deps_auth import get_mailer
from src.core.config import get_settings
from src.db.database import get_db
from src.main import app
from src.models.event import EventType, SeverityLevel
from src.repositories.event_repository import EventRepository
from src.services.community.mailer import LogMailer

DB_URL = os.getenv("TEST_DATABASE_URL", "").replace("postgresql://", "postgresql+asyncpg://", 1)
pytestmark = pytest.mark.skipif(not DB_URL, reason="TEST_DATABASE_URL not set")

ADMIN = "admin@phoenix.test"
COMMUNITY_TABLES = "connects, disclosures, offers, needs, org_memberships, orgs, user_sessions, magic_link_tokens, users"


@pytest.fixture
async def world():
    engine = create_async_engine(DB_URL, poolclass=NullPool)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as s:
        await s.execute(text(f"TRUNCATE {COMMUNITY_TABLES}, events, event_sources, data_sources CASCADE"))
        event = await EventRepository(s).create(
            type=EventType.flood, title="Flood", severity=SeverityLevel.high,
            start_date=datetime(2026, 10, 1, tzinfo=UTC), is_active=True, lat=24.9, lng=91.9,
        )
        await s.commit()
        event_id = str(event.id)

    async def override_db():
        async with maker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    mailer = LogMailer()
    settings = get_settings().model_copy(update={"platform_admin_emails": [ADMIN], "magic_link_max_per_hour": 5})
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_mailer] = lambda: mailer
    app.dependency_overrides[get_settings] = lambda: settings
    yield {"event_id": event_id, "mailer": mailer}
    app.dependency_overrides.clear()
    await engine.dispose()


def sign_in(mailer: LogMailer, email: str) -> TestClient:
    client = TestClient(app)
    r = client.post("/api/v1/auth/login-link", json={"email": email, "redirect_path": "/connect"})
    assert r.status_code == 202
    to, _, body = mailer.sent[-1]
    assert to == email
    token = re.search(r"token=([\w-]+)", body).group(1)
    r = client.post("/api/v1/auth/verify", json={"token": token})
    assert r.status_code == 200, r.text
    assert r.json()["redirect_path"] == "/connect"
    # One-time: the same link fails afterwards
    assert client.post("/api/v1/auth/verify", json={"token": token}).status_code == 400
    return client


def test_full_flow(world):
    mailer, event_id = world["mailer"], world["event_id"]
    anon = TestClient(app)

    alice = sign_in(mailer, "alice@ngo.test")
    bob = sign_in(mailer, "bob@donor.test")
    admin = sign_in(mailer, ADMIN)
    assert admin.get("/api/v1/auth/me").json()["is_platform_admin"] is True
    assert alice.get("/api/v1/auth/me").json()["is_platform_admin"] is False

    # Apply, cannot post before approval
    org = alice.post(
        "/api/v1/community/orgs",
        json={"name": "Water Relief", "org_type": "local_partner", "primary_email": "Contact@WaterRelief.test"},
    ).json()
    assert org["status"] == "pending"
    need_body = {
        "org_id": org["id"], "event_id": event_id, "title": "Water purification kits",
        "categories": ["water", "sanitation"], "priority": "critical", "quantity": 100, "unit": "kits",
        "latitude": 24.9, "longitude": 91.9, "place_name": "Camp 4",
    }
    assert alice.post("/api/v1/community/needs", json=need_body).status_code == 403

    # Only platform admins review
    assert alice.post(f"/api/v1/community/admin/orgs/{org['id']}/approve").status_code == 403
    pending = admin.get("/api/v1/community/admin/orgs", params={"status": "pending"}).json()
    assert [o["requested_by_email"] for o in pending] == ["alice@ngo.test"]
    assert admin.post(f"/api/v1/community/admin/orgs/{org['id']}/approve").json()["status"] == "approved"

    need = alice.post("/api/v1/community/needs", json=need_body)
    assert need.status_code == 201, need.text
    need = need.json()
    assert need["can_edit"] is True
    assert need["categories"] == ["water", "sanitation"]

    # Offers: sign-in required; private offers stay private
    assert anon.post("/api/v1/community/offers", json={}).status_code == 401
    offer_body = {
        "title": "200 purification kits", "offer_type": "goods", "categories": ["water"],
        "quantity": 200, "unit": "Kits", "latitude": 23.8, "longitude": 90.4, "event_id": event_id,
    }
    offer = bob.post("/api/v1/community/offers", json=offer_body).json()
    assert offer["is_mine"] is True
    bob.post("/api/v1/community/offers", json={"title": "Teachers", "offer_type": "volunteer", "categories": ["education"]})
    bob.post("/api/v1/community/offers", json={**offer_body, "title": "Hidden", "visibility": "private"})

    # Public reading, with the organisation's contact address
    listed = anon.get("/api/v1/community/needs", params={"event_id": event_id, "category": "water"}).json()
    assert listed["total"] == 1
    assert listed["data"][0]["contact_email"] == "contact@waterrelief.test"
    assert listed["data"][0]["can_edit"] is False
    assert anon.get("/api/v1/community/offers").json()["total"] == 2

    matches = anon.get(f"/api/v1/community/needs/{need['id']}/matches").json()["data"]
    assert [m["offer"]["title"] for m in matches] == ["200 purification kits"]
    assert "covers_all" in matches[0]["reasons"] and "same_event" in matches[0]["reasons"]

    # Bob proposes; his side is approved, nobody sees addresses yet
    c = bob.post("/api/v1/community/connects", json={"need_id": need["id"], "offer_id": offer["id"]})
    assert c.status_code == 201, c.text
    c = c.json()
    assert c["status"] == "pending" and c["offer_approved"] and not c["need_approved"]
    assert c["counterpart_email"] is None
    dup = bob.post("/api/v1/community/connects", json={"need_id": need["id"], "offer_id": offer["id"]})
    assert dup.status_code == 409
    assert mailer.sent[-1][0] == "contact@waterrelief.test"

    # Bob approving again changes nothing; strangers cannot see it
    assert bob.post(f"/api/v1/community/connects/{c['id']}/approve").json()["status"] == "pending"
    carol = sign_in(mailer, "carol@else.test")
    assert carol.post(f"/api/v1/community/connects/{c['id']}/approve").status_code == 404

    # Alice approves: both now see the other side's address
    done = alice.post(f"/api/v1/community/connects/{c['id']}/approve").json()
    assert done["status"] == "approved"
    assert done["counterpart_email"] == "bob@donor.test"
    bob_view = bob.get("/api/v1/community/connects").json()["data"][0]
    assert bob_view["counterpart_email"] == "contact@waterrelief.test"
    assert {m[0] for m in mailer.sent[-2:]} == {"bob@donor.test", "contact@waterrelief.test"}

    # Members-only needs
    alice.post("/api/v1/community/needs", json={**need_body, "title": "Internal", "visibility": "org_only"})
    assert anon.get("/api/v1/community/needs").json()["total"] == 1
    assert alice.get("/api/v1/community/needs").json()["total"] == 2

    # Disclosures
    d = alice.post(
        f"/api/v1/community/events/{event_id}/disclosures",
        json={"org_id": org["id"], "title": "Week 1", "body": "Delivered 200 kits to Camp 4."},
    )
    assert d.status_code == 201
    assert bob.post(
        f"/api/v1/community/events/{event_id}/disclosures",
        json={"org_id": org["id"], "title": "Fake", "body": "Not a member of this org."},
    ).status_code == 403
    assert [x["title"] for x in anon.get(f"/api/v1/community/events/{event_id}/disclosures").json()["data"]] == ["Week 1"]

    # Logout ends the session
    assert alice.post("/api/v1/auth/logout").status_code == 204
    assert alice.get("/api/v1/auth/me").status_code == 401


def test_login_link_rate_limit_and_bad_input(world):
    client = TestClient(app)
    for _ in range(5):
        assert client.post("/api/v1/auth/login-link", json={"email": "x@y.test"}).status_code == 202
    before = len(world["mailer"].sent)
    # Same answer, but no more mail
    assert client.post("/api/v1/auth/login-link", json={"email": "X@y.test"}).status_code == 202
    assert len(world["mailer"].sent) == before
    assert client.post("/api/v1/auth/login-link", json={"email": "not-an-email"}).status_code == 422
    assert client.post("/api/v1/auth/verify", json={"token": "x" * 43}).status_code == 400
