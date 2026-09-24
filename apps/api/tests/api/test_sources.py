"""Source status endpoint and freshness classification."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.v1.sources import source_health

NOW = datetime(2026, 9, 24, 12, 0, tzinfo=UTC)


def _source(**over):
    base = dict(
        name="USGS", type="disaster_alert", is_realtime=True, last_sync=NOW - timedelta(minutes=2),
        last_sync_status="success", last_sync_error=None, consecutive_failures=0,
        sync_interval_minutes=5,
    )
    base.update(over)
    return SimpleNamespace(**base)


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        ({}, "fresh"),
        ({"last_sync": None, "last_sync_status": "never"}, "never"),
        ({"last_sync_status": "failed", "consecutive_failures": 2}, "failing"),
        # 3 missed 5-minute syncs, but the 15-minute floor still applies
        ({"last_sync": NOW - timedelta(minutes=14)}, "fresh"),
        ({"last_sync": NOW - timedelta(minutes=16)}, "stale"),
        # Copernicus syncs every 30 min: stale only after 90 min
        ({"sync_interval_minutes": 30, "last_sync": NOW - timedelta(minutes=80)}, "fresh"),
        ({"sync_interval_minutes": 30, "last_sync": NOW - timedelta(minutes=95)}, "stale"),
    ],
)
def test_source_health(overrides, expected) -> None:
    assert source_health(_source(**overrides), NOW) == expected


def test_endpoint_lists_sources_and_hides_error_unless_failing(client: TestClient) -> None:
    sources = [
        _source(name="usgs", last_sync=datetime.now(UTC)),
        _source(
            name="GDACS", last_sync=datetime.now(UTC), last_sync_status="failed",
            consecutive_failures=1, last_sync_error="ExternalAPIError",
        ),
    ]
    with patch(
        "src.api.v1.sources.DataSourceRepository.list_active", AsyncMock(return_value=sources)
    ):
        response = client.get("/api/v1/sources")

    assert response.status_code == 200
    body = response.json()
    assert [s["name"] for s in body] == ["GDACS", "usgs"]  # case-insensitive order
    assert body[0]["status"] == "failing" and body[0]["last_error"] == "ExternalAPIError"
    assert body[1]["status"] == "fresh" and body[1]["last_error"] is None
