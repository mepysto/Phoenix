"""Event list ordering and filter counts (TEST_DATABASE_URL, disposable DB).

The disaster list leads with what matters most (UX plan 5.2): severity, then
people affected, then recency. Filter chips show how many events each choice
would give, given the other filters.
"""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from src.main import app
from src.models.event import EventType, SeverityLevel
from src.repositories.event_repository import EventRepository
from src.schemas.event import EventFilter
from tests.integration import test_plans_api as plans

pytestmark = plans.pytestmark
world = plans.world  # points the app at the test database

NOW = datetime.now(UTC)
# title, type, severity, days ago, people affected
ROWS = [
    ("low-recent", EventType.earthquake, SeverityLevel.low, 0, None),
    ("critical-old", EventType.flood, SeverityLevel.critical, 30, None),
    ("high-500", EventType.flood, SeverityLevel.high, 10, 500),
    ("high-100", EventType.earthquake, SeverityLevel.high, 5, 100),
    ("high-none", EventType.wildfire, SeverityLevel.high, 1, None),
]


@pytest.fixture
async def repo(world):
    engine = create_async_engine(plans.DB_URL, poolclass=NullPool)
    async with async_sessionmaker(engine, expire_on_commit=False)() as session:
        await session.execute(text("TRUNCATE events, event_sources, data_sources CASCADE"))
        repository = EventRepository(session)
        for title, kind, severity, ago, people in ROWS:
            await repository.create(
                type=kind, title=title, severity=severity, start_date=NOW - timedelta(days=ago),
                lat=0.0, lng=0.0, affected_population=people,
            )
        await session.commit()
        yield repository
    await engine.dispose()


async def _titles(repo: EventRepository, sort: str) -> list[str]:
    events, _ = await repo.list_events(EventFilter(), limit=50, offset=0, sort=sort)
    return [e.title for e in events]


async def test_importance_puts_severity_first_then_people_then_recency(repo):
    assert await _titles(repo, "importance") == [
        "critical-old",
        "high-500",
        "high-100",
        "high-none",  # no estimate sorts after estimates within its level
        "low-recent",
    ]


async def test_recent_and_affected_orders(repo):
    assert await _titles(repo, "recent") == ["low-recent", "high-none", "high-100", "high-500", "critical-old"]
    assert (await _titles(repo, "affected"))[:2] == ["high-500", "high-100"]


def _counts(rows: list[dict]) -> dict[str, int]:
    return {row["value"]: row["count"] for row in rows}


async def test_facets_count_each_dimension_under_the_other_filters(repo):
    facets = await repo.facets(EventFilter(types=[EventType.flood], severities=[SeverityLevel.high]))

    # Type counts ignore the type filter but keep the severity filter
    assert _counts(facets["by_type"]) == {"flood": 1, "earthquake": 1, "wildfire": 1}
    # Severity counts ignore the severity filter but keep the type filter
    assert _counts(facets["by_severity"]) == {"critical": 1, "high": 1}
    assert facets["total"] == 1


async def test_api_sort_and_facets(repo):
    client = TestClient(app)

    r = client.get("/api/v1/events", params={"sort": "importance", "limit": 2})
    assert r.status_code == 200
    assert [e["title"] for e in r.json()["data"]] == ["critical-old", "high-500"]

    assert client.get("/api/v1/events", params={"sort": "loudest"}).status_code == 422

    f = client.get("/api/v1/events/facets", params={"severities": ["high", "critical"]})
    assert f.status_code == 200
    body = f.json()
    assert body["total"] == 4
    assert _counts(body["by_type"]) == {"flood": 2, "earthquake": 1, "wildfire": 1}
    assert _counts(body["by_severity"]) == {"low": 1, "high": 3, "critical": 1}
    # Most frequent first
    assert body["by_severity"][0] == {"value": "high", "count": 3}
