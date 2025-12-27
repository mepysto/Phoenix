"""
Tests for the EventService business logic.
"""
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from src.schemas.event import EventFilter, EventListResponse, EventResponse
from src.services.event_service import EventService


class TestEventServiceListEvents:
    """Tests for EventService.list_events method."""

    @pytest.fixture
    def event_service(self) -> EventService:
        """Create an EventService instance for testing."""
        return EventService()

    @pytest.mark.asyncio
    async def test_list_events_returns_all_events(
        self, event_service: EventService
    ) -> None:
        """Test listing all events without filters."""
        filters = EventFilter()
        result = await event_service.list_events(filters, limit=50, offset=0)

        assert isinstance(result, EventListResponse)
        assert len(result.data) > 0
        assert result.pagination.total > 0

    @pytest.mark.asyncio
    async def test_list_events_filter_by_type(
        self, event_service: EventService
    ) -> None:
        """Test filtering events by type."""
        filters = EventFilter(types=["earthquake"])
        result = await event_service.list_events(filters, limit=50, offset=0)

        for event in result.data:
            assert event.type == "earthquake"

    @pytest.mark.asyncio
    async def test_list_events_filter_by_severity(
        self, event_service: EventService
    ) -> None:
        """Test filtering events by severity."""
        filters = EventFilter(severities=["high"])
        result = await event_service.list_events(filters, limit=50, offset=0)

        for event in result.data:
            assert event.severity == "high"

    @pytest.mark.asyncio
    async def test_list_events_filter_by_is_active(
        self, event_service: EventService
    ) -> None:
        """Test filtering events by active status."""
        filters = EventFilter(is_active=True)
        result = await event_service.list_events(filters, limit=50, offset=0)

        for event in result.data:
            assert event.is_active is True

    @pytest.mark.asyncio
    async def test_list_events_pagination_limit(
        self, event_service: EventService
    ) -> None:
        """Test pagination limit works correctly."""
        filters = EventFilter()
        result = await event_service.list_events(filters, limit=1, offset=0)

        assert len(result.data) <= 1
        assert result.pagination.limit == 1

    @pytest.mark.asyncio
    async def test_list_events_pagination_offset(
        self, event_service: EventService
    ) -> None:
        """Test pagination offset works correctly."""
        filters = EventFilter()

        # Get first page
        result1 = await event_service.list_events(filters, limit=1, offset=0)
        # Get second page
        result2 = await event_service.list_events(filters, limit=1, offset=1)

        assert result1.pagination.offset == 0
        assert result2.pagination.offset == 1

        # Ensure different events if both have data
        if result1.data and result2.data:
            assert result1.data[0].id != result2.data[0].id

    @pytest.mark.asyncio
    async def test_list_events_has_more_flag(
        self, event_service: EventService
    ) -> None:
        """Test has_more pagination flag."""
        filters = EventFilter()
        result = await event_service.list_events(filters, limit=1, offset=0)

        # If total > limit + offset, has_more should be True
        expected_has_more = result.pagination.total > (
            result.pagination.limit + result.pagination.offset
        )
        assert result.pagination.has_more == expected_has_more

    @pytest.mark.asyncio
    async def test_list_events_multiple_type_filters(
        self, event_service: EventService
    ) -> None:
        """Test filtering by multiple event types."""
        filters = EventFilter(types=["earthquake", "flood"])
        result = await event_service.list_events(filters, limit=50, offset=0)

        for event in result.data:
            assert event.type in ["earthquake", "flood"]


class TestEventServiceGetEvent:
    """Tests for EventService.get_event method."""

    @pytest.fixture
    def event_service(self) -> EventService:
        """Create an EventService instance for testing."""
        return EventService()

    @pytest.mark.asyncio
    async def test_get_event_not_found(self, event_service: EventService) -> None:
        """Test getting non-existent event returns None."""
        random_id = uuid4()
        result = await event_service.get_event(random_id)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_event_returns_detail_response(
        self, event_service: EventService
    ) -> None:
        """Test that get_event returns EventDetailResponse type."""
        # First get an event from the list
        filters = EventFilter()
        list_result = await event_service.list_events(filters, limit=1, offset=0)

        if list_result.data:
            event_id = list_result.data[0].id
            result = await event_service.get_event(event_id)

            if result:
                assert hasattr(result, "layers")
                assert hasattr(result, "datasets")
                assert hasattr(result, "metrics")


class TestEventServiceGetEventLayers:
    """Tests for EventService.get_event_layers method."""

    @pytest.fixture
    def event_service(self) -> EventService:
        """Create an EventService instance for testing."""
        return EventService()

    @pytest.mark.asyncio
    async def test_get_event_layers_returns_list(
        self, event_service: EventService
    ) -> None:
        """Test get_event_layers returns a list."""
        random_id = uuid4()
        result = await event_service.get_event_layers(random_id)

        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_get_event_layers_empty_for_new_event(
        self, event_service: EventService
    ) -> None:
        """Test get_event_layers returns empty list (current implementation)."""
        random_id = uuid4()
        result = await event_service.get_event_layers(random_id)

        assert result == []


class TestEventServiceMockEvents:
    """Tests for EventService mock data generation."""

    @pytest.fixture
    def event_service(self) -> EventService:
        """Create an EventService instance for testing."""
        return EventService()

    def test_mock_events_have_required_fields(
        self, event_service: EventService
    ) -> None:
        """Test mock events have all required fields."""
        mock_events = event_service._get_mock_events()

        assert len(mock_events) > 0
        for event in mock_events:
            assert event.id is not None
            assert event.type is not None
            assert event.title is not None
            assert event.location is not None
            assert event.severity is not None
            assert event.start_date is not None
            assert event.is_active is not None
            assert event.sources is not None
            assert event.created_at is not None
            assert event.updated_at is not None

    def test_mock_events_have_valid_location(
        self, event_service: EventService
    ) -> None:
        """Test mock events have valid location data."""
        mock_events = event_service._get_mock_events()

        for event in mock_events:
            assert -90 <= event.location.lat <= 90
            assert -180 <= event.location.lng <= 180
            assert event.location.country is not None
