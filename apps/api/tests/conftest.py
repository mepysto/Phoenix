"""
Common pytest fixtures for Phoenix API tests.
"""
from collections.abc import Generator
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.schemas.event import (
    DataSourceRef,
    DisplayPoint,
    EventDetailResponse,
    EventListResponse,
    EventResponse,
    Location,
    Pagination,
)
from src.services.event_service import EventService
from src.services.gdacs_service import GDACSEvent, GDACSService


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """Create a TestClient for synchronous API testing."""
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


@pytest.fixture
def mock_event_response() -> EventResponse:
    """Create a sample EventResponse for testing."""
    now = datetime.now(timezone.utc)
    return EventResponse(
        id=uuid4(),
        type="earthquake",
        title="Test Earthquake Event",
        description="Test earthquake for unit testing",
        location=Location(lat=35.0, lng=135.0, country="Japan", country_code="JP"),
        geo_precision="exact",
        display_point=DisplayPoint(lat=35.0, lng=135.0, source="event"),
        severity="high",
        affected_population=10000,
        start_date=now,
        is_active=True,
        sources=[DataSourceRef(id=uuid4(), name="GDACS", type="disaster_alert")],
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def mock_event_detail_response(mock_event_response: EventResponse) -> EventDetailResponse:
    """Create a sample EventDetailResponse for testing."""
    return EventDetailResponse(
        **mock_event_response.model_dump(),
        layers=[],
        datasets=[],
        metrics=[],
    )


@pytest.fixture
def mock_event_list_response(mock_event_response: EventResponse) -> EventListResponse:
    """Create a sample EventListResponse for testing."""
    return EventListResponse(
        data=[mock_event_response],
        pagination=Pagination(total=1, limit=50, offset=0, has_more=False),
    )


@pytest.fixture
def sample_events() -> list[EventResponse]:
    """Create multiple sample events for testing filtering."""
    now = datetime.now(timezone.utc)
    return [
        EventResponse(
            id=uuid4(),
            type="earthquake",
            title="Earthquake in Turkey",
            description="Major earthquake",
            location=Location(lat=37.5, lng=37.0, country="Turkey", country_code="TR"),
            geo_precision="exact",
            display_point=DisplayPoint(lat=37.5, lng=37.0, source="event"),
            severity="high",
            affected_population=50000,
            start_date=now,
            is_active=True,
            sources=[DataSourceRef(id=uuid4(), name="GDACS", type="disaster_alert")],
            created_at=now,
            updated_at=now,
        ),
        EventResponse(
            id=uuid4(),
            type="flood",
            title="Flooding in Bangladesh",
            description="Monsoon flooding",
            location=Location(lat=23.8, lng=90.4, country="Bangladesh", country_code="BD"),
            geo_precision="approximate",
            display_point=DisplayPoint(lat=23.8, lng=90.4, source="event"),
            severity="critical",
            affected_population=200000,
            start_date=now,
            is_active=True,
            sources=[DataSourceRef(id=uuid4(), name="GDACS", type="disaster_alert")],
            created_at=now,
            updated_at=now,
        ),
        EventResponse(
            id=uuid4(),
            type="wildfire",
            title="Wildfire in California",
            description="Large wildfire",
            location=Location(lat=39.5, lng=-121.5, country="United States", country_code="US"),
            geo_precision="admin1",
            display_point=DisplayPoint(lat=39.5, lng=-121.5, source="event"),
            severity="medium",
            affected_population=10000,
            start_date=now,
            is_active=False,
            sources=[DataSourceRef(id=uuid4(), name="GDACS", type="disaster_alert")],
            created_at=now,
            updated_at=now,
        ),
    ]


@pytest.fixture
def mock_event_service() -> MagicMock:
    """Create a mock EventService.
    
    Note: EventService now requires a session parameter in __init__.
    This mock is used for testing without DB connection.
    """
    service = MagicMock(spec=EventService)
    service.list_events = AsyncMock()
    service.get_event = AsyncMock()
    service.get_event_layers = AsyncMock(return_value=[])
    return service


@pytest.fixture
def mock_gdacs_service() -> MagicMock:
    """Create a mock GDACSService."""
    service = MagicMock(spec=GDACSService)
    service.fetch_rss_events = AsyncMock()
    service.fetch_api_events = AsyncMock()
    service.sync_events = AsyncMock()
    return service


@pytest.fixture
def sample_gdacs_event() -> GDACSEvent:
    """Create a sample GDACS event for testing."""
    return GDACSEvent(
        external_id="EQ123456",
        event_type="earthquake",
        title="M 6.5 - Japan",
        description="Moderate earthquake near Tokyo",
        lat=35.6762,
        lng=139.6503,
        country="Japan",
        severity="high",
        population=1000000,
        start_date=datetime.now(timezone.utc),
        url="https://www.gdacs.org/report.aspx?eventid=123456",
        raw_data={"event_type_code": "EQ", "alert_level": "Red"},
    )


@pytest.fixture
def sample_gdacs_rss_xml() -> str:
    """Sample GDACS RSS XML for testing RSS parsing."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" 
    xmlns:gdacs="http://www.gdacs.org"
    xmlns:geo="http://www.w3.org/2003/01/geo/wgs84_pos#"
    xmlns:dc="http://purl.org/dc/elements/1.1/">
  <channel>
    <title>GDACS - RSS Feed</title>
    <item>
      <title>M 6.2 - Turkey</title>
      <description>Earthquake near Ankara</description>
      <link>https://www.gdacs.org/report.aspx?eventid=EQ001</link>
      <gdacs:eventtype>EQ</gdacs:eventtype>
      <gdacs:alertlevel>Orange</gdacs:alertlevel>
      <gdacs:eventid>EQ001</gdacs:eventid>
      <gdacs:country>Turkey</gdacs:country>
      <gdacs:population>50000</gdacs:population>
      <geo:lat>39.9334</geo:lat>
      <geo:long>32.8597</geo:long>
      <gdacs:fromdate>2024-01-15T10:30:00Z</gdacs:fromdate>
    </item>
    <item>
      <title>Flood Alert - Bangladesh</title>
      <description>Severe flooding in Dhaka region</description>
      <link>https://www.gdacs.org/report.aspx?eventid=FL002</link>
      <gdacs:eventtype>FL</gdacs:eventtype>
      <gdacs:alertlevel>Red</gdacs:alertlevel>
      <gdacs:eventid>FL002</gdacs:eventid>
      <gdacs:country>Bangladesh</gdacs:country>
      <gdacs:population>200000</gdacs:population>
      <geo:lat>23.8103</geo:lat>
      <geo:long>90.4125</geo:long>
      <gdacs:fromdate>2024-01-14T08:00:00Z</gdacs:fromdate>
    </item>
  </channel>
</rss>"""


@pytest.fixture
def api_sync_key() -> str:
    """Return the test API sync key."""
    return "dev-sync-key"
