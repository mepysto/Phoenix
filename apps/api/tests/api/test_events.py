"""
Tests for the Events API endpoints.

These tests use dependency_overrides to mock the EventService,
allowing tests to run without a real database connection.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from src.api.v1.events import get_event_service
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


def create_mock_event_response(
    event_type: str = "earthquake",
    severity: str = "high",
    is_active: bool = True,
) -> EventResponse:
    """Helper to create a mock EventResponse."""
    now = datetime.now(timezone.utc)
    return EventResponse(
        id=uuid4(),
        type=event_type,
        title=f"Test {event_type.capitalize()} Event",
        description=f"Test {event_type} for unit testing",
        location=Location(lat=35.0, lng=135.0, country="Japan", country_code="JP"),
        geo_precision="exact",
        display_point=DisplayPoint(lat=35.0, lng=135.0, source="event"),
        severity=severity,
        affected_population=10000,
        start_date=now,
        is_active=is_active,
        sources=[DataSourceRef(id=uuid4(), name="GDACS", type="disaster_alert")],
        created_at=now,
        updated_at=now,
    )


def create_mock_event_service(events: list[EventResponse] | None = None) -> MagicMock:
    """Create a mock EventService with configurable events."""
    if events is None:
        events = [
            create_mock_event_response("earthquake", "high", True),
            create_mock_event_response("flood", "critical", True),
            create_mock_event_response("wildfire", "medium", False),
        ]

    service = MagicMock(spec=EventService)

    async def mock_list_events(filters, limit, offset):
        filtered = events
        if filters.types:
            filtered = [e for e in filtered if e.type in filters.types]
        if filters.severities:
            filtered = [e for e in filtered if e.severity in filters.severities]
        if filters.is_active is not None:
            filtered = [e for e in filtered if e.is_active == filters.is_active]

        total = len(filtered)
        paginated = filtered[offset : offset + limit]
        return EventListResponse(
            data=paginated,
            pagination=Pagination(
                total=total, limit=limit, offset=offset, has_more=offset + limit < total
            ),
        )

    async def mock_get_event(event_id):
        for event in events:
            if event.id == event_id:
                return EventDetailResponse(
                    **event.model_dump(), layers=[], datasets=[], metrics=[]
                )
        return None

    async def mock_get_event_layers(event_id):
        return []

    service.list_events = mock_list_events
    service.get_event = mock_get_event
    service.get_event_layers = mock_get_event_layers

    return service


@pytest.fixture
def mock_service():
    """Create a mock event service for testing."""
    return create_mock_event_service()


@pytest.fixture
def client_with_mock_service(mock_service):
    """Create a TestClient with mocked EventService."""

    def override_get_event_service():
        return mock_service

    app.dependency_overrides[get_event_service] = override_get_event_service
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
    app.dependency_overrides.clear()


class TestListEvents:
    """Tests for GET /api/v1/events endpoint."""

    def test_list_events_success(self, client_with_mock_service: TestClient) -> None:
        """Test successful listing of events."""
        response = client_with_mock_service.get("/api/v1/events")
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data
        assert isinstance(data["data"], list)
        assert "total" in data["pagination"]
        assert "limit" in data["pagination"]
        assert "offset" in data["pagination"]

    def test_list_events_with_type_filter(
        self, client_with_mock_service: TestClient
    ) -> None:
        """Test listing events with type filter."""
        response = client_with_mock_service.get(
            "/api/v1/events", params={"types": ["earthquake"]}
        )
        assert response.status_code == 200
        data = response.json()
        for event in data["data"]:
            assert event["type"] == "earthquake"

    def test_list_events_with_severity_filter(
        self, client_with_mock_service: TestClient
    ) -> None:
        """Test listing events with severity filter."""
        response = client_with_mock_service.get(
            "/api/v1/events", params={"severities": ["high"]}
        )
        assert response.status_code == 200
        data = response.json()
        for event in data["data"]:
            assert event["severity"] == "high"

    def test_list_events_with_is_active_filter(
        self, client_with_mock_service: TestClient
    ) -> None:
        """Test listing events with is_active filter."""
        response = client_with_mock_service.get(
            "/api/v1/events", params={"is_active": True}
        )
        assert response.status_code == 200
        data = response.json()
        for event in data["data"]:
            assert event["is_active"] is True

    def test_list_events_with_pagination(
        self, client_with_mock_service: TestClient
    ) -> None:
        """Test listing events with pagination parameters."""
        response = client_with_mock_service.get(
            "/api/v1/events", params={"limit": 10, "offset": 0}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["pagination"]["limit"] == 10
        assert data["pagination"]["offset"] == 0

    def test_list_events_limit_validation(
        self, client_with_mock_service: TestClient
    ) -> None:
        """Test that limit exceeding max returns validation error."""
        response = client_with_mock_service.get(
            "/api/v1/events", params={"limit": 500}
        )
        assert response.status_code == 422

    def test_list_events_offset_validation(
        self, client_with_mock_service: TestClient
    ) -> None:
        """Test that negative offset returns validation error."""
        response = client_with_mock_service.get(
            "/api/v1/events", params={"offset": -1}
        )
        assert response.status_code == 422

    def test_list_events_with_multiple_types(
        self, client_with_mock_service: TestClient
    ) -> None:
        """Test listing events with multiple type filters."""
        response = client_with_mock_service.get(
            "/api/v1/events", params={"types": ["earthquake", "flood"]}
        )
        assert response.status_code == 200
        data = response.json()
        for event in data["data"]:
            assert event["type"] in ["earthquake", "flood"]

    def test_list_events_with_radius_search(
        self, client_with_mock_service: TestClient
    ) -> None:
        """Test listing events with radius search parameters."""
        response = client_with_mock_service.get(
            "/api/v1/events",
            params={"center_lat": 35.0, "center_lng": 139.0, "radius_km": 100},
        )
        assert response.status_code == 200

    def test_list_events_radius_km_validation(
        self, client_with_mock_service: TestClient
    ) -> None:
        """Test that radius_km exceeding max returns validation error."""
        response = client_with_mock_service.get(
            "/api/v1/events",
            params={"center_lat": 35.0, "center_lng": 139.0, "radius_km": 600},
        )
        assert response.status_code == 422

    def test_list_events_response_has_geo_precision(
        self, client_with_mock_service: TestClient
    ) -> None:
        """Test that events response includes geo_precision field."""
        response = client_with_mock_service.get("/api/v1/events")
        assert response.status_code == 200
        data = response.json()
        for event in data["data"]:
            assert "geo_precision" in event

    def test_list_events_response_has_display_point(
        self, client_with_mock_service: TestClient
    ) -> None:
        """Test that events response includes display_point field."""
        response = client_with_mock_service.get("/api/v1/events")
        assert response.status_code == 200
        data = response.json()
        for event in data["data"]:
            assert "display_point" in event
            if event["display_point"]:
                assert "lat" in event["display_point"]
                assert "lng" in event["display_point"]
                assert "source" in event["display_point"]


class TestGetEvent:
    """Tests for GET /api/v1/events/{event_id} endpoint."""

    def test_get_event_not_found(self, client_with_mock_service: TestClient) -> None:
        """Test getting a non-existent event returns 404."""
        random_uuid = uuid4()
        response = client_with_mock_service.get(f"/api/v1/events/{random_uuid}")
        assert response.status_code == 404
        assert "detail" in response.json()
        assert response.json()["detail"] == "Event not found"

    def test_get_event_invalid_uuid(
        self, client_with_mock_service: TestClient
    ) -> None:
        """Test getting an event with invalid UUID returns 422."""
        response = client_with_mock_service.get("/api/v1/events/not-a-valid-uuid")
        assert response.status_code == 422

    def test_get_event_success(self, client_with_mock_service: TestClient) -> None:
        """Test getting an existing event returns its details."""
        # First, get the list to find an existing event ID
        list_response = client_with_mock_service.get("/api/v1/events")
        assert list_response.status_code == 200
        events = list_response.json()["data"]
        assert len(events) > 0

        # Get the first event's details
        event_id = events[0]["id"]
        response = client_with_mock_service.get(f"/api/v1/events/{event_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == event_id
        assert "layers" in data
        assert "datasets" in data
        assert "metrics" in data


class TestGetEventLayers:
    """Tests for GET /api/v1/events/{event_id}/layers endpoint."""

    def test_get_event_layers_returns_empty_list(
        self, client_with_mock_service: TestClient
    ) -> None:
        """Test getting event layers (currently returns empty list)."""
        random_uuid = uuid4()
        response = client_with_mock_service.get(f"/api/v1/events/{random_uuid}/layers")
        assert response.status_code == 200
        data = response.json()
        assert "layers" in data
        assert isinstance(data["layers"], list)

    def test_get_event_layers_invalid_uuid(
        self, client_with_mock_service: TestClient
    ) -> None:
        """Test getting layers with invalid UUID returns 422."""
        response = client_with_mock_service.get("/api/v1/events/invalid-uuid/layers")
        assert response.status_code == 422


class TestHealthEndpoint:
    """Tests for the health check endpoint."""

    def test_health_check(self, client_with_mock_service: TestClient) -> None:
        """Test health endpoint returns healthy status."""
        response = client_with_mock_service.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


class TestSchedulerStatus:
    """Tests for the scheduler status endpoint."""

    def test_scheduler_status(self, client_with_mock_service: TestClient) -> None:
        """Test scheduler status endpoint returns valid response."""
        response = client_with_mock_service.get("/scheduler/status")
        assert response.status_code == 200
        data = response.json()
        assert "running" in data or "status" in data or "last_sync" in data
