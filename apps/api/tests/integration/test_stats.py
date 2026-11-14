"""Overview dashboard figures (TEST_DATABASE_URL)."""

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from src.main import app
from src.models.event import EventType, SeverityLevel
from src.repositories.event_repository import EventRepository
from tests.integration import test_plans_api as plans

ADMIN, pytestmark = plans.ADMIN, plans.pytestmark
world = plans.world  # shared fixture: users, one active high flood (no population), test settings


async def _add_events():
    engine = create_async_engine(plans.DB_URL, poolclass=NullPool)
    now = datetime.now(UTC)
    async with async_sessionmaker(engine, expire_on_commit=False)() as s:
        repo = EventRepository(s)
        rows = [
            # type, severity, days ago, affected, country, active
            (EventType.earthquake, SeverityLevel.critical, 2, 300_000, "TUR", True),
            (EventType.earthquake, SeverityLevel.medium, 3, 1_000, "TUR", True),
            (EventType.wildfire, SeverityLevel.high, 10, 50_000, "AUS", True),
            (EventType.drought, SeverityLevel.low, 40, 2_000_000, "KEN", False),  # ended: not "active"
            (EventType.flood, SeverityLevel.low, 400, 9, "BGD", True),  # older than the 12-week window
        ]
        for t, sev, ago, people, cc, active in rows:
            e = await repo.create(
                type=t, title=f"{t.value}-{ago}", severity=sev, start_date=now - timedelta(days=ago),
                lat=0.0, lng=0.0, affected_population=people, country_code=cc, is_active=active,
            )
            e.country_code = cc
        await s.commit()
    await engine.dispose()


async def test_overview_counts_public_active_data(world):
    await _add_events()
    mailer = world["mailer"]
    ana = plans.sign_in(mailer, "ana@ngo.test")
    admin = plans.sign_in(mailer, ADMIN)
    org = ana.post("/api/v1/community/orgs", json={"name": "Relief", "org_type": "local_partner", "primary_email": "r@ngo.test"}).json()
    admin.post(f"/api/v1/community/admin/orgs/{org['id']}/approve")
    ana.post("/api/v1/community/needs", json={"org_id": org["id"], "title": "Water", "categories": ["water", "sanitation"]})
    ana.post("/api/v1/community/needs", json={"org_id": org["id"], "title": "Food", "categories": ["food"]})
    ana.post(
        "/api/v1/community/needs",
        json={"org_id": org["id"], "title": "Staff only", "categories": ["water"], "visibility": "org_only"},
    )

    r = TestClient(app).get("/api/v1/stats/overview")
    assert r.status_code == 200
    assert "max-age=60" in r.headers["cache-control"]
    s = r.json()

    # world's flood + earthquakes x2 + wildfire + old flood; the ended drought is excluded
    assert s["active_events"] == 5
    assert s["critical_active"] == 1
    assert s["affected_active"] == 300_000 + 1_000 + 50_000 + 9
    # The dashboard says "not yet counted" rather than 0 when no event has an estimate
    assert s["affected_estimated"] == 4  # world's flood has no population figure
    assert s["countries_active"] == 3  # TUR, AUS, BGD (world's flood has no country)
    assert [x["severity"] for x in s["by_severity"]] == ["low", "medium", "high", "critical"]
    assert {x["severity"]: x["events"] for x in s["by_severity"]} == {"low": 1, "medium": 1, "high": 2, "critical": 1}
    assert s["by_type"][0] == {"type": "earthquake", "events": 2, "affected": 301_000}

    weeks = s["weekly_onsets"]
    assert len(weeks) == 12 and sum(w["events"] for w in weeks) >= 4  # the 400-day-old flood is outside
    assert weeks == sorted(weeks, key=lambda w: w["week_start"])
    assert s["new_this_week"] == 2 and s["new_week_before"] == 1

    assert [e["affected"] for e in s["top_affected"]] == [300_000, 50_000, 1_000, 9]

    # Public needs of approved orgs only; categories counted per need
    assert s["needs_open"] == 2  # org_only is excluded
    cats = {c["category"]: c["open"] for c in s["needs_by_category"]}
    assert cats == {"water": 1, "sanitation": 1, "food": 1}

    # An organisation that loses approval drops out of the public figures
    admin.post(f"/api/v1/community/admin/orgs/{org['id']}/reject", json={"reason": "test"})
    assert TestClient(app).get("/api/v1/stats/overview").json()["needs_open"] == 0
