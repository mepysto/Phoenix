"""Site plans: create, version, fork, visibility, attach to a need (TEST_DATABASE_URL)."""

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
ITEMS = [[0, 24.9, 91.9], [1, 24.901, 91.9], [2, 24.9, 91.901]]


@pytest.fixture
async def world():
    engine = create_async_engine(DB_URL, poolclass=NullPool)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as s:
        await s.execute(text(
            "TRUNCATE challenge_votes, challenge_entries, challenges, site_plan_versions, site_plans, connects, disclosures, offers, needs, org_memberships, "
            "orgs, user_sessions, magic_link_tokens, users, events, event_sources, data_sources CASCADE"
        ))
        event = await EventRepository(s).create(
            type=EventType.flood, title="Flood", severity=SeverityLevel.high,
            start_date=datetime(2026, 10, 1, tzinfo=UTC), is_active=True, lat=24.9, lng=91.9,
        )
        await s.commit()

    async def override_db():
        async with maker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    mailer = LogMailer()
    settings = get_settings().model_copy(update={"platform_admin_emails": [ADMIN]})
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_mailer] = lambda: mailer
    app.dependency_overrides[get_settings] = lambda: settings
    yield {"event_id": str(event.id), "mailer": mailer}
    app.dependency_overrides.clear()
    await engine.dispose()


def sign_in(mailer, email):
    c = TestClient(app)
    c.post("/api/v1/auth/login-link", json={"email": email})
    token = re.search(r"token=([\w-]+)", mailer.sent[-1][2]).group(1)
    assert c.post("/api/v1/auth/verify", json={"token": token}).status_code == 200
    return c


def test_plan_lifecycle(world):
    mailer, event_id = world["mailer"], world["event_id"]
    anon = TestClient(app)
    ana = sign_in(mailer, "ana@ngo.test")
    bo = sign_in(mailer, "bo@eng.test")

    assert anon.post("/api/v1/plans", json={}).status_code == 401
    bad = ana.post("/api/v1/plans", json={"title": "Bad", "population": 10, "items": [[9, 0, 0]]})
    assert bad.status_code == 422

    plan = ana.post("/api/v1/plans", json={
        "title": "Camp 4 layout", "event_id": event_id, "population": 500, "items": ITEMS, "note": "first cut",
    }).json()
    assert plan["version"] == 1 and plan["item_count"] == 3 and plan["is_mine"]

    v2 = ana.post(f"/api/v1/plans/{plan['id']}/versions", json={"population": 600, "items": ITEMS + [[3, 24.9, 91.902]]}).json()
    assert v2["latest_version"] == 2 and v2["item_count"] == 4
    assert [v["number"] for v in v2["versions"]] == [2, 1]
    old = anon.get(f"/api/v1/plans/{plan['id']}", params={"version": 1}).json()
    assert old["version"] == 1 and old["population"] == 500 and old["note"] == "first cut"

    # Only the author saves versions; others fork
    assert bo.post(f"/api/v1/plans/{plan['id']}/versions", json={"population": 1, "items": []}).status_code == 403
    fork = bo.post(f"/api/v1/plans/{plan['id']}/fork", json={"version": 1}).json()
    assert fork["forked_from_id"] == plan["id"] and fork["forked_from_version"] == 1
    assert fork["population"] == 500 and fork["is_mine"]
    assert len(anon.get("/api/v1/plans", params={"event_id": event_id}).json()["data"]) == 2

    # Private plans are hidden from others
    ana.patch(f"/api/v1/plans/{plan['id']}", json={"visibility": "private"})
    assert anon.get(f"/api/v1/plans/{plan['id']}").status_code == 404
    assert ana.get(f"/api/v1/plans/{plan['id']}").status_code == 200

    # Attach a public plan to a need; private ones are refused
    admin = sign_in(mailer, ADMIN)
    org = ana.post("/api/v1/community/orgs", json={"name": "Relief", "org_type": "local_partner", "primary_email": "r@relief.test"}).json()
    admin.post(f"/api/v1/community/admin/orgs/{org['id']}/approve")
    need = ana.post("/api/v1/community/needs", json={"org_id": org["id"], "title": "Shelter for 500", "categories": ["shelter"]}).json()
    assert ana.patch(f"/api/v1/community/needs/{need['id']}", json={"plan_id": plan["id"]}).status_code == 404
    done = ana.patch(f"/api/v1/community/needs/{need['id']}", json={"plan_id": fork["id"]}).json()
    assert done["plan_id"] == fork["id"]
    assert ana.patch(f"/api/v1/community/needs/{need['id']}", json={"plan_id": None}).json()["plan_id"] is None
