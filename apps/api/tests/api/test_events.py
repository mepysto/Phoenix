"""
Tests for the Events API endpoints.
"""
from typing import Any
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from src.schemas.event import (
    EventDetailResponse,
    EventListResponse,
    EventResponse,
    Pagination,
)


class TestListEvents:
    """Tests for GET /api/v1/events endpoint."""

    def test_list_events_success(self, client: TestClient) -> None:
        """Test successful listing of events."""
        response = client.get("/api/v1/events")
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data
        assert isinstance(data["data"], list)
        assert "total" in data["pagination"]
        assert "limit" in data["pagination"]
        assert "offset" in data["pagination"]

    def test_list_events_with_type_filter(self, client: TestClient) -> None:
        """Test listing events with type filter."""
        response = client.get("/api/v1/events", params={"types": ["earthquake"]})
        assert response.status_code == 200
        data = response.json()
        for event in data["data"]:
            assert event["type"] == "earthquake"

    def test_list_events_with_severity_filter(self, client: TestClient) -> None:
        """Test listing events with severity filter."""
        response = client.get("/api/v1/events", params={"severities": ["high"]})
        assert response.status_code == 200
        data = response.json()
        for event in data["data"]:
            assert event["severity"] == "high"

    def test_list_events_with_is_active_filter(self, client: TestClient) -> None:
        """Test listing events with is_active filter."""
        response = client.get("/api/v1/events", params={"is_active": True})
        assert response.status_code == 200
        data = response.json()
        for event in data["data"]:
            assert event["is_active"] is True

    def test_list_events_with_pagination(self, client: TestClient) -> None:
        """Test listing events with pagination parameters."""
        response = client.get("/api/v1/events", params={"limit": 10, "offset": 0})
        assert response.status_code == 200
        data = response.json()
        assert data["pagination"]["limit"] == 10
        assert data["pagination"]["offset"] == 0

    def test_list_events_limit_validation(self, client: TestClient) -> None:
        """Test that limit exceeding max returns validation error."""
        response = client.get("/api/v1/events", params={"limit": 500})
        assert response.status_code == 422

    def test_list_events_offset_validation(self, client: TestClient) -> None:
        """Test that negative offset returns validation error."""
        response = client.get("/api/v1/events", params={"offset": -1})
        assert response.status_code == 422

    def test_list_events_with_multiple_types(self, client: TestClient) -> None:
        """Test listing events with multiple type filters."""
        response = client.get(
            "/api/v1/events", params={"types": ["earthquake", "flood"]}
        )
        assert response.status_code == 200
        data = response.json()
        for event in data["data"]:
            assert event["type"] in ["earthquake", "flood"]


class TestGetEvent:
    """Tests for GET /api/v1/events/{event_id} endpoint."""

    def test_get_event_not_found(self, client: TestClient) -> None:
        """Test getting a non-existent event returns 404."""
        random_uuid = uuid4()
        response = client.get(f"/api/v1/events/{random_uuid}")
        assert response.status_code == 404
        assert "detail" in response.json()
        assert response.json()["detail"] == "Event not found"

    def test_get_event_invalid_uuid(self, client: TestClient) -> None:
        """Test getting an event with invalid UUID returns 422."""
        response = client.get("/api/v1/events/not-a-valid-uuid")
        assert response.status_code == 422


class TestGetEventLayers:
    """Tests for GET /api/v1/events/{event_id}/layers endpoint."""

    def test_get_event_layers_returns_empty_list(self, client: TestClient) -> None:
        """Test getting event layers (currently returns empty list)."""
        random_uuid = uuid4()
        response = client.get(f"/api/v1/events/{random_uuid}/layers")
        assert response.status_code == 200
        data = response.json()
        assert "layers" in data
        assert isinstance(data["layers"], list)

    def test_get_event_layers_invalid_uuid(self, client: TestClient) -> None:
        """Test getting layers with invalid UUID returns 422."""
        response = client.get("/api/v1/events/invalid-uuid/layers")
        assert response.status_code == 422


class TestHealthEndpoint:
    """Tests for the health check endpoint."""

    def test_health_check(self, client: TestClient) -> None:
        """Test health endpoint returns healthy status."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


class TestSchedulerStatus:
    """Tests for the scheduler status endpoint."""

    def test_scheduler_status(self, client: TestClient) -> None:
        """Test scheduler status endpoint returns valid response."""
        response = client.get("/scheduler/status")
        assert response.status_code == 200
        data = response.json()
        assert "running" in data or "status" in data or "last_sync" in data
