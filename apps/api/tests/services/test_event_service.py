"""
Tests for the EventService business logic.

The EventService now uses database repositories. These tests use mocked
repositories to test the service logic without requiring a real database.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.models.event import Event, EventSource, EventType, GeoPrecision, SeverityLevel
from src.schemas.event import (
    EventDetailResponse,
    EventFilter,
    EventListResponse,
    EventResponse,
)
from src.services.event_service import EventService


def create_mock_event(
    event_type: EventType = EventType.earthquake,
    severity: SeverityLevel = SeverityLevel.high,
    is_active: bool = True,
    geo_precision: GeoPrecision = GeoPrecision.exact,
) -> Event:
    """Create a mock Event model for testing."""
    now = datetime.now(timezone.utc)
    event = MagicMock(spec=Event)
    event.id = uuid4()
    event.type = event_type
    event.title = f"Test {event_type.value.capitalize()} Event"
    event.description = f"Test {event_type.value} for unit testing"
    event.latitude = 35.0
    event.longitude = 135.0
    event.region = "Japan"
    event.country_code = "JP"
    event.severity = severity
    event.geo_precision = geo_precision
    event.affected_population = 10000
    event.start_date = now
    event.end_date = None
    event.is_active = is_active
    event.sources = []
    event.created_at = now
    event.updated_at = now
    return event


def create_mock_event_with_source(
    event_type: EventType = EventType.earthquake,
) -> Event:
    """Create a mock Event with a DataSource."""
    event = create_mock_event(event_type)

    # Create mock DataSource
    data_source = MagicMock()
    data_source.id = uuid4()
    data_source.name = "GDACS"
    data_source.type = "disaster_alert"

    # Create mock EventSource linking event to data source
    event_source = MagicMock(spec=EventSource)
    event_source.source = data_source

    event.sources = [event_source]
    return event


class TestEventServiceListEvents:
    """Tests for EventService.list_events method."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock database session."""
        return MagicMock()

    @pytest.fixture
    def event_service(self, mock_session) -> EventService:
        """Create an EventService instance with mocked repository."""
        service = EventService(mock_session)
        service.event_repo = MagicMock()
        return service

    @pytest.mark.asyncio
    async def test_list_events_returns_event_list_response(
        self, event_service: EventService
    ) -> None:
        """Test listing events returns EventListResponse."""
        mock_events = [
            create_mock_event(EventType.earthquake),
            create_mock_event(EventType.flood),
        ]
        event_service.event_repo.list_events = AsyncMock(
            return_value=(mock_events, len(mock_events))
        )

        filters = EventFilter()
        result = await event_service.list_events(filters, limit=50, offset=0)

        assert isinstance(result, EventListResponse)
        assert len(result.data) == 2
        assert result.pagination.total == 2

    @pytest.mark.asyncio
    async def test_list_events_calls_repo_with_sources(
        self, event_service: EventService
    ) -> None:
        """Test that list_events calls repository with with_sources=True."""
        event_service.event_repo.list_events = AsyncMock(return_value=([], 0))

        filters = EventFilter(types=["earthquake"])
        await event_service.list_events(filters, limit=50, offset=0)

        event_service.event_repo.list_events.assert_called_once_with(
            filters, 50, 0, with_sources=True
        )

    @pytest.mark.asyncio
    async def test_list_events_converts_model_to_response(
        self, event_service: EventService
    ) -> None:
        """Test that Event models are converted to EventResponse."""
        mock_event = create_mock_event_with_source()
        event_service.event_repo.list_events = AsyncMock(
            return_value=([mock_event], 1)
        )

        filters = EventFilter()
        result = await event_service.list_events(filters, limit=50, offset=0)

        assert len(result.data) == 1
        response = result.data[0]
        assert isinstance(response, EventResponse)
        assert response.type == "earthquake"
        assert response.location.lat == 35.0
        assert response.location.lng == 135.0
        assert len(response.sources) == 1
        assert response.sources[0].name == "GDACS"

    @pytest.mark.asyncio
    async def test_list_events_pagination_has_more(
        self, event_service: EventService
    ) -> None:
        """Test has_more pagination flag is calculated correctly."""
        mock_events = [create_mock_event()]
        event_service.event_repo.list_events = AsyncMock(
            return_value=(mock_events, 10)  # 10 total, returning 1
        )

        filters = EventFilter()
        result = await event_service.list_events(filters, limit=1, offset=0)

        assert result.pagination.has_more is True
        assert result.pagination.total == 10

    @pytest.mark.asyncio
    async def test_list_events_pagination_no_more(
        self, event_service: EventService
    ) -> None:
        """Test has_more is False when no more results."""
        mock_events = [create_mock_event()]
        event_service.event_repo.list_events = AsyncMock(
            return_value=(mock_events, 1)
        )

        filters = EventFilter()
        result = await event_service.list_events(filters, limit=50, offset=0)

        assert result.pagination.has_more is False

    @pytest.mark.asyncio
    async def test_list_events_empty_results(
        self, event_service: EventService
    ) -> None:
        """Test handling of empty results."""
        event_service.event_repo.list_events = AsyncMock(return_value=([], 0))

        filters = EventFilter()
        result = await event_service.list_events(filters, limit=50, offset=0)

        assert len(result.data) == 0
        assert result.pagination.total == 0
        assert result.pagination.has_more is False


class TestEventServiceGetEvent:
    """Tests for EventService.get_event method."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock database session."""
        return MagicMock()

    @pytest.fixture
    def event_service(self, mock_session) -> EventService:
        """Create an EventService instance with mocked repository."""
        service = EventService(mock_session)
        service.event_repo = MagicMock()
        return service

    @pytest.mark.asyncio
    async def test_get_event_not_found(self, event_service: EventService) -> None:
        """Test getting non-existent event returns None."""
        event_service.event_repo.get_by_id_with_sources = AsyncMock(return_value=None)

        random_id = uuid4()
        result = await event_service.get_event(random_id)

        assert result is None
        event_service.event_repo.get_by_id_with_sources.assert_called_once_with(
            random_id
        )

    @pytest.mark.asyncio
    async def test_get_event_returns_detail_response(
        self, event_service: EventService
    ) -> None:
        """Test get_event returns EventDetailResponse with layers, datasets, metrics."""
        mock_event = create_mock_event_with_source()
        event_service.event_repo.get_by_id_with_sources = AsyncMock(
            return_value=mock_event
        )

        result = await event_service.get_event(mock_event.id)

        assert result is not None
        assert isinstance(result, EventDetailResponse)
        assert hasattr(result, "layers")
        assert hasattr(result, "datasets")
        assert hasattr(result, "metrics")
        # Phase 2 returns empty lists
        assert result.layers == []
        assert result.datasets == []
        assert result.metrics == []

    @pytest.mark.asyncio
    async def test_get_event_converts_sources(
        self, event_service: EventService
    ) -> None:
        """Test that sources are properly converted."""
        mock_event = create_mock_event_with_source()
        event_service.event_repo.get_by_id_with_sources = AsyncMock(
            return_value=mock_event
        )

        result = await event_service.get_event(mock_event.id)

        assert result is not None
        assert len(result.sources) == 1
        assert result.sources[0].name == "GDACS"
        assert result.sources[0].type == "disaster_alert"


class TestEventServiceGetEventLayers:
    """Tests for EventService.get_event_layers method."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock database session."""
        return MagicMock()

    @pytest.fixture
    def event_service(self, mock_session) -> EventService:
        """Create an EventService instance."""
        return EventService(mock_session)

    @pytest.mark.asyncio
    async def test_get_event_layers_returns_empty_list(
        self, event_service: EventService
    ) -> None:
        """Test get_event_layers returns empty list in Phase 2."""
        random_id = uuid4()
        result = await event_service.get_event_layers(random_id)

        assert isinstance(result, list)
        assert result == []


class TestEventServiceToResponse:
    """Tests for EventService._to_response method."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock database session."""
        return MagicMock()

    @pytest.fixture
    def event_service(self, mock_session) -> EventService:
        """Create an EventService instance."""
        return EventService(mock_session)

    def test_to_response_handles_none_coordinates(
        self, event_service: EventService
    ) -> None:
        """Test _to_response handles None lat/lng gracefully."""
        event = create_mock_event()
        event.latitude = None
        event.longitude = None

        response = event_service._to_response(event)

        assert response.location.lat is None
        assert response.location.lng is None
        assert response.display_point is None

    def test_to_response_extracts_event_type_value(
        self, event_service: EventService
    ) -> None:
        """Test _to_response extracts enum value for type."""
        event = create_mock_event(EventType.wildfire)

        response = event_service._to_response(event)

        assert response.type == "wildfire"

    def test_to_response_extracts_severity_value(
        self, event_service: EventService
    ) -> None:
        """Test _to_response extracts enum value for severity."""
        event = create_mock_event(severity=SeverityLevel.critical)

        response = event_service._to_response(event)

        assert response.severity == "critical"

    def test_to_response_handles_empty_sources(
        self, event_service: EventService
    ) -> None:
        """Test _to_response handles events with no sources."""
        event = create_mock_event()
        event.sources = []

        response = event_service._to_response(event)

        assert response.sources == []
