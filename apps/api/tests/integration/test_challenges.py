"""Design challenges: open, enter, vote, close, select (TEST_DATABASE_URL)."""

import re
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from src.main import app
from tests.integration import test_plans_api as plans

ADMIN, ITEMS, pytestmark, DB_URL = plans.ADMIN, plans.ITEMS, plans.pytestmark, plans.DB_URL
world = plans.world  # shared fixture


def sign_in(mailer, email):
    c = TestClient(app)
    c.post("/api/v1/auth/login-link", json={"email": email})
    token = re.search(r"token=([\w-]+)", mailer.sent[-1][2]).group(1)
    assert c.post("/api/v1/auth/verify", json={"token": token}).status_code == 200
    return c


async def test_challenge_flow(world):
    mailer, event_id = world["mailer"], world["event_id"]
    host = sign_in(mailer, "host@ngo.test")
    ana = sign_in(mailer, "ana@eng.test")
    bo = sign_in(mailer, "bo@eng.test")
    cy = sign_in(mailer, "cy@eng.test")
    admin = sign_in(mailer, ADMIN)
    org = host.post("/api/v1/community/orgs", json={"name": "Camp NGO", "org_type": "local_partner", "primary_email": "c@ngo.test"}).json()

    body = {
        "org_id": org["id"], "event_id": event_id, "title": "Camp for 2,000 people",
        "brief": "Design a temporary camp next to the river bend.", "population": 2000,
        "closes_at": (datetime.now(UTC) + timedelta(days=7)).isoformat(),
    }
    assert host.post("/api/v1/challenges", json=body).status_code == 403  # org not approved yet
    admin.post(f"/api/v1/community/admin/orgs/{org['id']}/approve")
    assert ana.post("/api/v1/challenges", json=body).status_code == 403  # not a member
    past = {**body, "closes_at": (datetime.now(UTC) - timedelta(hours=1)).isoformat()}
    assert host.post("/api/v1/challenges", json=past).status_code == 422
    ch = host.post("/api/v1/challenges", json=body).json()
    assert ch["is_open"] and ch["can_manage"] and ch["entries"] == []

    p_ana = ana.post("/api/v1/plans", json={"title": "Ana layout", "population": 2000, "items": ITEMS}).json()
    p_bo = bo.post("/api/v1/plans", json={"title": "Bo layout", "population": 2000, "items": ITEMS}).json()
    p_priv = bo.post("/api/v1/plans", json={"title": "Draft", "population": 1, "items": ITEMS, "visibility": "private"}).json()

    assert bo.post(f"/api/v1/challenges/{ch['id']}/entries", json={"plan_id": p_ana["id"]}).status_code == 404  # not his
    assert bo.post(f"/api/v1/challenges/{ch['id']}/entries", json={"plan_id": p_priv["id"]}).status_code == 409
    ana.post(f"/api/v1/challenges/{ch['id']}/entries", json={"plan_id": p_ana["id"]})
    assert ana.post(f"/api/v1/challenges/{ch['id']}/entries", json={"plan_id": p_ana["id"]}).status_code == 409
    got = bo.post(f"/api/v1/challenges/{ch['id']}/entries", json={"plan_id": p_bo["id"]}).json()
    entry = {e["plan_title"]: e for e in got["entries"]}

    assert ana.post(f"/api/v1/challenges/entries/{entry['Ana layout']['id']}/vote").status_code == 409  # own
    cy.post(f"/api/v1/challenges/entries/{entry['Bo layout']['id']}/vote")
    cy.post(f"/api/v1/challenges/entries/{entry['Bo layout']['id']}/vote")  # idempotent
    ranked = ana.post(f"/api/v1/challenges/entries/{entry['Bo layout']['id']}/vote").json()
    assert [(e["plan_title"], e["votes"]) for e in ranked["entries"]] == [("Bo layout", 2), ("Ana layout", 0)]
    assert ranked["entries"][0]["voted_by_me"] is True
    undone = cy.post(f"/api/v1/challenges/entries/{entry['Bo layout']['id']}/unvote").json()
    assert undone["entries"][0]["votes"] == 1

    # Host selects; others cannot
    assert ana.post(f"/api/v1/challenges/{ch['id']}/select", json={"entry_id": entry["Ana layout"]["id"]}).status_code == 403
    sel = host.post(f"/api/v1/challenges/{ch['id']}/select", json={"entry_id": entry["Ana layout"]["id"]}).json()
    assert sel["entries"][0]["plan_title"] == "Ana layout" and sel["entries"][0]["selected"]

    listed = TestClient(app).get("/api/v1/challenges", params={"event_id": event_id}).json()["data"]
    assert listed[0]["entry_count"] == 2 and listed[0]["has_selection"]

    # After the deadline: no entries, no votes
    engine = create_async_engine(DB_URL, poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.execute(text("UPDATE challenges SET closes_at = now() - interval '1 hour'"))
    await engine.dispose()
    assert cy.post(f"/api/v1/challenges/entries/{entry['Ana layout']['id']}/vote").status_code == 409
    p_cy = cy.post("/api/v1/plans", json={"title": "Late", "population": 10, "items": ITEMS}).json()
    assert cy.post(f"/api/v1/challenges/{ch['id']}/entries", json={"plan_id": p_cy["id"]}).status_code == 409
    assert TestClient(app).get(f"/api/v1/challenges/{ch['id']}").json()["is_open"] is False
