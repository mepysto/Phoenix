"""Verified partners and contribution badges (TEST_DATABASE_URL)."""

import re

from fastapi.testclient import TestClient

from src.main import app
from tests.integration import test_plans_api as plans

ADMIN, ITEMS, pytestmark = plans.ADMIN, plans.ITEMS, plans.pytestmark
world = plans.world  # shared fixture: users, an event, test settings


def sign_in(mailer, email):
    c = TestClient(app)
    c.post("/api/v1/auth/login-link", json={"email": email})
    token = re.search(r"token=([\w-]+)", mailer.sent[-1][2]).group(1)
    assert c.post("/api/v1/auth/verify", json={"token": token}).status_code == 200
    return c


def test_verify_partner_and_contributions(world):
    mailer, event_id = world["mailer"], world["event_id"]
    ana = sign_in(mailer, "ana@unhcr.test")
    bo = sign_in(mailer, "bo@donor.test")
    admin = sign_in(mailer, ADMIN)

    org = ana.post("/api/v1/community/orgs", json={"name": "UN Agency", "org_type": "un", "primary_email": "x@un.test"}).json()
    # Only approved orgs can be verified, and only by admins
    assert admin.post(f"/api/v1/community/admin/orgs/{org['id']}/verify").status_code == 409
    admin.post(f"/api/v1/community/admin/orgs/{org['id']}/approve")
    assert ana.post(f"/api/v1/community/admin/orgs/{org['id']}/verify").status_code == 403
    assert admin.post(f"/api/v1/community/admin/orgs/{org['id']}/verify").json()["verified"] is True

    need = ana.post("/api/v1/community/needs", json={"org_id": org["id"], "title": "Water for camp", "categories": ["water"]}).json()
    assert need["org"]["verified"] is True
    offer = bo.post("/api/v1/community/offers", json={"title": "Filters", "offer_type": "goods", "categories": ["water"]}).json()
    c = bo.post("/api/v1/community/connects", json={"need_id": need["id"], "offer_id": offer["id"]}).json()
    ana.post(f"/api/v1/community/connects/{c['id']}/approve")
    plan = bo.post("/api/v1/plans", json={"title": "Camp layout", "event_id": event_id, "population": 100, "items": ITEMS}).json()
    ana.post(f"/api/v1/plans/{plan['id']}/fork", json={})

    mine = bo.get("/api/v1/auth/me/contributions").json()
    assert mine["counts"] == {"offers": 1, "needs": 0, "connections": 1, "plans_public": 1, "forks_received": 1, "disclosures": 0}
    assert mine["points"] == 1 + 5 + 3 + 2
    assert {b["id"] for b in mine["badges"] if b["earned"]} == {"first_offer", "connector", "planner"}
    assert TestClient(app).get("/api/v1/auth/me/contributions").status_code == 401

    assert admin.post(f"/api/v1/community/admin/orgs/{org['id']}/unverify").json()["verified"] is False
