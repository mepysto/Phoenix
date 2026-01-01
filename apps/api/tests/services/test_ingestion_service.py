"""
Tests for the IngestionService.
"""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.models.event import EventType, GeoPrecision, GeoMethod, SeverityLevel
from src.services.connectors.base import RawEvent
from src.services.copernicus_service import CopernicusEvent
from src.services.gdacs_service import GDACSEvent
from src.services.ingestion_service import (
    IngestionResult,
    IngestionService,
    GDACS_EVENT_TYPE_MAP,
    GDACS_SEVERITY_MAP,
    COPERNICUS_EVENT_TYPE_MAP,
    COPERNICUS_SEVERITY_MAP,
    USGS_EVENT_TYPE_MAP,
    EONET_EVENT_TYPE_MAP,
)


class TestIngestionResult:
    """Tests for IngestionResult dataclass."""

    def test_default_values(self) -> None:
        """Test default values are initialized correctly."""
        result = IngestionResult()
        assert result.created == 0
        assert result.updated == 0
        assert result.failed == 0
        assert result.errors == []

    def test_add_error(self) -> None:
        """Test add_error method."""
        result = IngestionResult()
        result.add_error("Test error 1")
        result.add_error("Test error 2")
        assert len(result.errors) == 2
        assert "Test error 1" in result.errors
        assert "Test error 2" in result.errors

    def test_to_dict(self) -> None:
        """Test to_dict conversion."""
        result = IngestionResult(created=5, updated=3, failed=1)
        result.add_error("Test error")
        
        d = result.to_dict()
        assert d["created"] == 5
        assert d["updated"] == 3
        assert d["failed"] == 1
        assert d["errors"] == ["Test error"]


class TestTypeMappings:
    """Tests for type mapping dictionaries."""

    def test_gdacs_event_type_map_completeness(self) -> None:
        """Test GDACS event type map covers expected types."""
        expected_types = ["earthquake", "flood", "hurricane", "volcano", "drought", "wildfire", "tsunami"]
        for event_type in expected_types:
            assert event_type in GDACS_EVENT_TYPE_MAP

    def test_gdacs_severity_map_completeness(self) -> None:
        """Test GDACS severity map covers expected levels."""
        expected_severities = ["low", "medium", "high", "critical"]
        for severity in expected_severities:
            assert severity in GDACS_SEVERITY_MAP

    def test_copernicus_event_type_map_completeness(self) -> None:
        """Test Copernicus event type map covers expected types."""
        expected_types = ["flood", "hurricane", "wildfire", "earthquake", "volcano", "drought", "landslide"]
        for event_type in expected_types:
            assert event_type in COPERNICUS_EVENT_TYPE_MAP

    def test_copernicus_severity_map_completeness(self) -> None:
        """Test Copernicus severity map covers expected levels."""
        expected_severities = ["low", "medium", "high", "critical"]
        for severity in expected_severities:
            assert severity in COPERNICUS_SEVERITY_MAP

    def test_usgs_event_type_map_has_earthquake(self) -> None:
        """Test USGS event type map has earthquake."""
        assert "earthquake" in USGS_EVENT_TYPE_MAP
        assert USGS_EVENT_TYPE_MAP["earthquake"] == EventType.earthquake

    def test_eonet_event_type_map_completeness(self) -> None:
        """Test EONET event type map covers expected types."""
        expected_types = [
            "drought", "earthquake", "flood", "landslide", "industrial",
            "storm", "heatwave", "volcano", "wildfire", "pollution", "other"
        ]
        for event_type in expected_types:
            assert event_type in EONET_EVENT_TYPE_MAP


class TestIngestionServiceTypeMappings:
    """Tests for IngestionService type mapping methods."""

    @pytest.fixture
    def service(self) -> IngestionService:
        """Create IngestionService with mock session."""
        mock_session = MagicMock()
        return IngestionService(mock_session)

    def test_map_gdacs_event_type_known(self, service: IngestionService) -> None:
        """Test mapping known GDACS event types."""
        assert service._map_gdacs_event_type("earthquake") == EventType.earthquake
        assert service._map_gdacs_event_type("flood") == EventType.flood
        assert service._map_gdacs_event_type("hurricane") == EventType.hurricane
        assert service._map_gdacs_event_type("wildfire") == EventType.wildfire

    def test_map_gdacs_event_type_unknown(self, service: IngestionService) -> None:
        """Test mapping unknown GDACS event type returns other."""
        assert service._map_gdacs_event_type("unknown_type") == EventType.other
        assert service._map_gdacs_event_type("") == EventType.other

    def test_map_gdacs_event_type_case_insensitive(self, service: IngestionService) -> None:
        """Test GDACS event type mapping is case insensitive."""
        assert service._map_gdacs_event_type("EARTHQUAKE") == EventType.earthquake
        assert service._map_gdacs_event_type("Flood") == EventType.flood

    def test_map_gdacs_severity_known(self, service: IngestionService) -> None:
        """Test mapping known GDACS severity levels."""
        assert service._map_gdacs_severity("low") == SeverityLevel.low
        assert service._map_gdacs_severity("medium") == SeverityLevel.medium
        assert service._map_gdacs_severity("high") == SeverityLevel.high
        assert service._map_gdacs_severity("critical") == SeverityLevel.critical

    def test_map_gdacs_severity_unknown(self, service: IngestionService) -> None:
        """Test mapping unknown GDACS severity returns medium."""
        assert service._map_gdacs_severity("unknown") == SeverityLevel.medium
        assert service._map_gdacs_severity("") == SeverityLevel.medium

    def test_map_copernicus_event_type_known(self, service: IngestionService) -> None:
        """Test mapping known Copernicus event types."""
        assert service._map_copernicus_event_type("flood") == EventType.flood
        assert service._map_copernicus_event_type("wildfire") == EventType.wildfire
        assert service._map_copernicus_event_type("landslide") == EventType.landslide

    def test_map_copernicus_event_type_unknown(self, service: IngestionService) -> None:
        """Test mapping unknown Copernicus event type returns other."""
        assert service._map_copernicus_event_type("unknown") == EventType.other

    def test_map_copernicus_severity_known(self, service: IngestionService) -> None:
        """Test mapping known Copernicus severity levels."""
        assert service._map_copernicus_severity("low") == SeverityLevel.low
        assert service._map_copernicus_severity("medium") == SeverityLevel.medium
        assert service._map_copernicus_severity("high") == SeverityLevel.high
        assert service._map_copernicus_severity("critical") == SeverityLevel.critical


class TestIngestionServiceGDACS:
    """Tests for GDACS event ingestion."""

    @pytest.fixture
    def mock_session(self) -> MagicMock:
        """Create a mock async session."""
        return MagicMock()

    @pytest.fixture
    def sample_gdacs_event(self) -> GDACSEvent:
        """Create a sample GDACS event."""
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

    @pytest.mark.asyncio
    async def test_ingest_gdacs_empty_list(self, mock_session: MagicMock) -> None:
        """Test ingesting empty list returns zero counts."""
        service = IngestionService(mock_session)
        result = await service.ingest_gdacs_events([])
        
        assert result["created"] == 0
        assert result["updated"] == 0
        assert result["failed"] == 0
        assert result["errors"] == []

    @pytest.mark.asyncio
    async def test_ingest_gdacs_creates_new_event(
        self, mock_session: MagicMock, sample_gdacs_event: GDACSEvent
    ) -> None:
        """Test ingesting new GDACS event creates event and event source."""
        service = IngestionService(mock_session)
        
        # Mock data source repository
        mock_data_source = MagicMock()
        mock_data_source.id = uuid4()
        service.data_source_repo.get_or_create = AsyncMock(return_value=mock_data_source)
        service.data_source_repo.update_sync_status = AsyncMock()
        
        # Mock event source repository - no existing event
        service.event_source_repo.find_event_id_by_source_external = AsyncMock(return_value=None)
        service.event_source_repo.upsert = AsyncMock()
        
        # Mock event repository
        mock_event = MagicMock()
        mock_event.id = uuid4()
        service.event_repo.create = AsyncMock(return_value=mock_event)
        
        result = await service.ingest_gdacs_events([sample_gdacs_event])
        
        assert result["created"] == 1
        assert result["updated"] == 0
        assert result["failed"] == 0
        
        # Verify event was created with correct parameters
        service.event_repo.create.assert_called_once()
        call_kwargs = service.event_repo.create.call_args.kwargs
        assert call_kwargs["type"] == EventType.earthquake
        assert call_kwargs["title"] == sample_gdacs_event.title
        assert call_kwargs["lat"] == sample_gdacs_event.lat
        assert call_kwargs["lng"] == sample_gdacs_event.lng
        assert call_kwargs["geo_precision"] == GeoPrecision.approximate
        assert call_kwargs["geo_method"] == GeoMethod.source_provided

    @pytest.mark.asyncio
    async def test_ingest_gdacs_updates_existing_event(
        self, mock_session: MagicMock, sample_gdacs_event: GDACSEvent
    ) -> None:
        """Test ingesting existing GDACS event updates event source."""
        service = IngestionService(mock_session)
        
        # Mock data source repository
        mock_data_source = MagicMock()
        mock_data_source.id = uuid4()
        service.data_source_repo.get_or_create = AsyncMock(return_value=mock_data_source)
        service.data_source_repo.update_sync_status = AsyncMock()
        
        # Mock event source repository - existing event found
        existing_event_id = uuid4()
        service.event_source_repo.find_event_id_by_source_external = AsyncMock(
            return_value=existing_event_id
        )
        service.event_source_repo.upsert = AsyncMock()
        
        # Mock event repository - update returns None (no improvement)
        service.event_repo.update_if_better = AsyncMock(return_value=None)
        
        result = await service.ingest_gdacs_events([sample_gdacs_event])
        
        assert result["created"] == 0
        assert result["updated"] == 1
        assert result["failed"] == 0
        
        # Verify upsert was called
        service.event_source_repo.upsert.assert_called_once()
        # Verify update_if_better was called
        service.event_repo.update_if_better.assert_called_once()


class TestIngestionServiceCopernicus:
    """Tests for Copernicus event ingestion."""

    @pytest.fixture
    def mock_session(self) -> MagicMock:
        """Create a mock async session."""
        return MagicMock()

    @pytest.fixture
    def sample_copernicus_event(self) -> CopernicusEvent:
        """Create a sample Copernicus event."""
        return CopernicusEvent(
            external_id="EMSR001",
            event_type="flood",
            title="Flood in Italy",
            description="Severe flooding in northern Italy",
            lat=45.4642,
            lng=9.1900,
            country="Italy",
            severity="high",
            n_aois=8,
            n_products=15,
            start_date=datetime.now(timezone.utc),
            url="https://rapidmapping.emergency.copernicus.eu/EMSR/EMSR001",
            raw_data={"code": "EMSR001", "category": {"slug": "flood"}},
        )

    @pytest.mark.asyncio
    async def test_ingest_copernicus_empty_list(self, mock_session: MagicMock) -> None:
        """Test ingesting empty list returns zero counts."""
        service = IngestionService(mock_session)
        result = await service.ingest_copernicus_events([])
        
        assert result["created"] == 0
        assert result["updated"] == 0
        assert result["failed"] == 0
        assert result["errors"] == []

    @pytest.mark.asyncio
    async def test_ingest_copernicus_creates_new_event(
        self, mock_session: MagicMock, sample_copernicus_event: CopernicusEvent
    ) -> None:
        """Test ingesting new Copernicus event creates event and event source."""
        service = IngestionService(mock_session)
        
        # Mock data source repository
        mock_data_source = MagicMock()
        mock_data_source.id = uuid4()
        service.data_source_repo.get_or_create = AsyncMock(return_value=mock_data_source)
        service.data_source_repo.update_sync_status = AsyncMock()
        
        # Mock event source repository - no existing event
        service.event_source_repo.find_event_id_by_source_external = AsyncMock(return_value=None)
        service.event_source_repo.upsert = AsyncMock()
        
        # Mock event repository
        mock_event = MagicMock()
        mock_event.id = uuid4()
        service.event_repo.create = AsyncMock(return_value=mock_event)
        
        result = await service.ingest_copernicus_events([sample_copernicus_event])
        
        assert result["created"] == 1
        assert result["updated"] == 0
        assert result["failed"] == 0
        
        # Verify event was created with correct parameters
        service.event_repo.create.assert_called_once()
        call_kwargs = service.event_repo.create.call_args.kwargs
        assert call_kwargs["type"] == EventType.flood
        assert call_kwargs["title"] == sample_copernicus_event.title
        assert call_kwargs["source_id"] == sample_copernicus_event.external_id
        assert call_kwargs["geo_precision"] == GeoPrecision.approximate
        assert call_kwargs["geo_method"] == GeoMethod.source_provided

    @pytest.mark.asyncio
    async def test_ingest_copernicus_non_atomic_continues_on_error(
        self, mock_session: MagicMock, sample_copernicus_event: CopernicusEvent
    ) -> None:
        """Test non-atomic mode continues processing after individual errors."""
        service = IngestionService(mock_session)
        
        # Mock data source repository
        mock_data_source = MagicMock()
        mock_data_source.id = uuid4()
        service.data_source_repo.get_or_create = AsyncMock(return_value=mock_data_source)
        service.data_source_repo.update_sync_status = AsyncMock()
        
        # First event fails, second succeeds
        call_count = 0
        async def mock_find_event_id(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Test error")
            return None
        
        service.event_source_repo.find_event_id_by_source_external = mock_find_event_id
        service.event_source_repo.upsert = AsyncMock()
        
        mock_event = MagicMock()
        mock_event.id = uuid4()
        service.event_repo.create = AsyncMock(return_value=mock_event)
        
        # Create two events
        events = [sample_copernicus_event, sample_copernicus_event]
        
        result = await service.ingest_copernicus_events(events, atomic=False)
        
        assert result["created"] == 1
        assert result["failed"] == 1
        assert len(result["errors"]) == 1
        assert "Test error" in result["errors"][0]


class TestIngestionServiceUSGS:
    """Tests for USGS event ingestion."""

    @pytest.fixture
    def mock_session(self) -> MagicMock:
        """Create a mock async session."""
        return MagicMock()

    @pytest.fixture
    def sample_usgs_event(self) -> RawEvent:
        """Create a sample USGS RawEvent."""
        return RawEvent(
            source_name="USGS",
            external_id="us7000abc123",
            title="M 5.5 - 100km NW of Tokyo, Japan",
            description="Magnitude 5.5 earthquake. Depth: 35.2 km. Location: 100km NW of Tokyo.",
            start_date=datetime.now(timezone.utc),
            source_url="https://earthquake.usgs.gov/earthquakes/eventpage/us7000abc123",
            lat=35.6762,
            lng=139.6503,
            event_type_raw="earthquake",
            severity_raw="yellow",
            magnitude=5.5,
            raw_data={"type": "Feature", "properties": {"mag": 5.5, "alert": "yellow"}},
        )

    @pytest.mark.asyncio
    async def test_ingest_usgs_empty_list(self, mock_session: MagicMock) -> None:
        """Test ingesting empty list returns zero counts."""
        service = IngestionService(mock_session)
        result = await service.ingest_usgs_events([])
        
        assert result["created"] == 0
        assert result["updated"] == 0
        assert result["failed"] == 0
        assert result["errors"] == []

    @pytest.mark.asyncio
    async def test_ingest_usgs_creates_new_event(
        self, mock_session: MagicMock, sample_usgs_event: RawEvent
    ) -> None:
        """Test ingesting new USGS event creates event and event source."""
        service = IngestionService(mock_session)
        
        # Mock data source repository
        mock_data_source = MagicMock()
        mock_data_source.id = uuid4()
        service.data_source_repo.get_or_create = AsyncMock(return_value=mock_data_source)
        service.data_source_repo.update_sync_status = AsyncMock()
        
        # Mock event source repository - no existing event
        service.event_source_repo.find_event_id_by_source_external = AsyncMock(return_value=None)
        service.event_source_repo.upsert = AsyncMock()
        
        # Mock event repository
        mock_event = MagicMock()
        mock_event.id = uuid4()
        service.event_repo.create = AsyncMock(return_value=mock_event)
        
        # Mock dedup service - no cross-source match
        service.dedup_service.find_matching_event = AsyncMock(return_value=None)
        
        result = await service.ingest_usgs_events([sample_usgs_event])
        
        assert result["created"] == 1
        assert result["updated"] == 0
        assert result["failed"] == 0
        
        # Verify event was created with correct parameters
        service.event_repo.create.assert_called_once()
        call_kwargs = service.event_repo.create.call_args.kwargs
        assert call_kwargs["type"] == EventType.earthquake
        assert call_kwargs["title"] == sample_usgs_event.title
        assert call_kwargs["lat"] == sample_usgs_event.lat
        assert call_kwargs["lng"] == sample_usgs_event.lng
        assert call_kwargs["geo_precision"] == GeoPrecision.approximate
        assert call_kwargs["geo_method"] == GeoMethod.source_provided
        # USGS severity is computed from magnitude (5.5 = medium)
        assert call_kwargs["severity"] == SeverityLevel.medium

    @pytest.mark.asyncio
    async def test_ingest_usgs_updates_existing_event(
        self, mock_session: MagicMock, sample_usgs_event: RawEvent
    ) -> None:
        """Test ingesting existing USGS event updates event source."""
        service = IngestionService(mock_session)
        
        # Mock data source repository
        mock_data_source = MagicMock()
        mock_data_source.id = uuid4()
        service.data_source_repo.get_or_create = AsyncMock(return_value=mock_data_source)
        service.data_source_repo.update_sync_status = AsyncMock()
        
        # Mock event source repository - existing event found
        existing_event_id = uuid4()
        service.event_source_repo.find_event_id_by_source_external = AsyncMock(
            return_value=existing_event_id
        )
        service.event_source_repo.upsert = AsyncMock()
        
        # Mock event repository - update returns None (no improvement)
        service.event_repo.update_if_better = AsyncMock(return_value=None)
        
        result = await service.ingest_usgs_events([sample_usgs_event])
        
        assert result["created"] == 0
        assert result["updated"] == 1
        assert result["failed"] == 0
        
        # Verify upsert was called
        service.event_source_repo.upsert.assert_called_once()
        # Verify update_if_better was called
        service.event_repo.update_if_better.assert_called_once()

    @pytest.mark.asyncio
    async def test_ingest_usgs_major_earthquake_severity(
        self, mock_session: MagicMock
    ) -> None:
        """Test that major earthquakes (M7+) get critical severity."""
        major_event = RawEvent(
            source_name="USGS",
            external_id="us7000major",
            title="M 7.5 - Major Earthquake",
            start_date=datetime.now(timezone.utc),
            lat=35.0,
            lng=135.0,
            event_type_raw="earthquake",
            magnitude=7.5,
            raw_data={},
        )
        
        service = IngestionService(mock_session)
        
        # Mock repositories
        mock_data_source = MagicMock()
        mock_data_source.id = uuid4()
        service.data_source_repo.get_or_create = AsyncMock(return_value=mock_data_source)
        service.data_source_repo.update_sync_status = AsyncMock()
        service.event_source_repo.find_event_id_by_source_external = AsyncMock(return_value=None)
        service.event_source_repo.upsert = AsyncMock()
        
        mock_event = MagicMock()
        mock_event.id = uuid4()
        service.event_repo.create = AsyncMock(return_value=mock_event)
        
        # Mock dedup service - no cross-source match
        service.dedup_service.find_matching_event = AsyncMock(return_value=None)
        
        await service.ingest_usgs_events([major_event])
        
        # Verify severity is critical for M7+
        call_kwargs = service.event_repo.create.call_args.kwargs
        assert call_kwargs["severity"] == SeverityLevel.critical


class TestIngestionServiceEONET:
    """Tests for EONET event ingestion."""

    @pytest.fixture
    def mock_session(self) -> MagicMock:
        """Create a mock async session."""
        return MagicMock()

    @pytest.fixture
    def sample_eonet_event(self) -> RawEvent:
        """Create a sample EONET RawEvent."""
        return RawEvent(
            source_name="EONET",
            external_id="EONET_6789",
            title="Wildfire - California, United States",
            description="Active wildfire in northern California | Sources: INCIWEB, NASA",
            start_date=datetime.now(timezone.utc),
            source_url="https://eonet.gsfc.nasa.gov/api/v3/events/EONET_6789",
            lat=38.5816,
            lng=-121.4944,
            event_type_raw="wildfire",
            raw_data={"properties": {"title": "Wildfire - California"}},
        )

    @pytest.mark.asyncio
    async def test_ingest_eonet_empty_list(self, mock_session: MagicMock) -> None:
        """Test ingesting empty list returns zero counts."""
        service = IngestionService(mock_session)
        result = await service.ingest_eonet_events([])
        
        assert result["created"] == 0
        assert result["updated"] == 0
        assert result["failed"] == 0
        assert result["errors"] == []

    @pytest.mark.asyncio
    async def test_ingest_eonet_creates_new_event(
        self, mock_session: MagicMock, sample_eonet_event: RawEvent
    ) -> None:
        """Test ingesting new EONET event creates event and event source."""
        service = IngestionService(mock_session)
        
        # Mock data source repository
        mock_data_source = MagicMock()
        mock_data_source.id = uuid4()
        service.data_source_repo.get_or_create = AsyncMock(return_value=mock_data_source)
        service.data_source_repo.update_sync_status = AsyncMock()
        
        # Mock event source repository - no existing event
        service.event_source_repo.find_event_id_by_source_external = AsyncMock(return_value=None)
        service.event_source_repo.upsert = AsyncMock()
        
        # Mock dedup service - no cross-source match
        service.dedup_service.find_matching_event = AsyncMock(return_value=None)
        
        # Mock event repository
        mock_event = MagicMock()
        mock_event.id = uuid4()
        service.event_repo.create = AsyncMock(return_value=mock_event)
        
        result = await service.ingest_eonet_events([sample_eonet_event])
        
        assert result["created"] == 1
        assert result["updated"] == 0
        assert result["failed"] == 0
        
        # Verify event was created with correct parameters
        service.event_repo.create.assert_called_once()
        call_kwargs = service.event_repo.create.call_args.kwargs
        assert call_kwargs["type"] == EventType.wildfire
        assert call_kwargs["title"] == sample_eonet_event.title
        assert call_kwargs["lat"] == sample_eonet_event.lat
        assert call_kwargs["lng"] == sample_eonet_event.lng
        assert call_kwargs["geo_precision"] == GeoPrecision.approximate
        assert call_kwargs["geo_method"] == GeoMethod.source_provided
        # EONET wildfires get high severity by default
        assert call_kwargs["severity"] == SeverityLevel.high

    @pytest.mark.asyncio
    async def test_ingest_eonet_updates_existing_event(
        self, mock_session: MagicMock, sample_eonet_event: RawEvent
    ) -> None:
        """Test ingesting existing EONET event updates event source."""
        service = IngestionService(mock_session)
        
        # Mock data source repository
        mock_data_source = MagicMock()
        mock_data_source.id = uuid4()
        service.data_source_repo.get_or_create = AsyncMock(return_value=mock_data_source)
        service.data_source_repo.update_sync_status = AsyncMock()
        
        # Mock event source repository - existing event found
        existing_event_id = uuid4()
        service.event_source_repo.find_event_id_by_source_external = AsyncMock(
            return_value=existing_event_id
        )
        service.event_source_repo.upsert = AsyncMock()
        
        # Mock event repository - update returns None (no improvement)
        service.event_repo.update_if_better = AsyncMock(return_value=None)
        
        result = await service.ingest_eonet_events([sample_eonet_event])
        
        assert result["created"] == 0
        assert result["updated"] == 1
        assert result["failed"] == 0
        
        # Verify upsert was called
        service.event_source_repo.upsert.assert_called_once()
        # Verify update_if_better was called
        service.event_repo.update_if_better.assert_called_once()

    @pytest.mark.asyncio
    async def test_ingest_eonet_closed_event_sets_inactive(
        self, mock_session: MagicMock
    ) -> None:
        """Test that closed EONET events are marked as inactive."""
        closed_event = RawEvent(
            source_name="EONET",
            external_id="EONET_closed",
            title="Closed Wildfire",
            start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2024, 1, 15, tzinfo=timezone.utc),  # Has end date
            lat=35.0,
            lng=-120.0,
            event_type_raw="wildfire",
            raw_data={},
        )
        
        service = IngestionService(mock_session)
        
        # Mock repositories
        mock_data_source = MagicMock()
        mock_data_source.id = uuid4()
        service.data_source_repo.get_or_create = AsyncMock(return_value=mock_data_source)
        service.data_source_repo.update_sync_status = AsyncMock()
        service.event_source_repo.find_event_id_by_source_external = AsyncMock(return_value=None)
        service.event_source_repo.upsert = AsyncMock()
        
        mock_event = MagicMock()
        mock_event.id = uuid4()
        service.event_repo.create = AsyncMock(return_value=mock_event)
        
        # Mock dedup service - no cross-source match
        service.dedup_service.find_matching_event = AsyncMock(return_value=None)
        
        await service.ingest_eonet_events([closed_event])
        
        # Verify is_active is False for closed events
        call_kwargs = service.event_repo.create.call_args.kwargs
        assert call_kwargs["is_active"] is False
        assert call_kwargs["end_date"] == closed_event.end_date

    @pytest.mark.asyncio
    async def test_ingest_eonet_non_atomic_continues_on_error(
        self, mock_session: MagicMock, sample_eonet_event: RawEvent
    ) -> None:
        """Test non-atomic mode continues processing after individual errors."""
        service = IngestionService(mock_session)
        
        # Mock data source repository
        mock_data_source = MagicMock()
        mock_data_source.id = uuid4()
        service.data_source_repo.get_or_create = AsyncMock(return_value=mock_data_source)
        service.data_source_repo.update_sync_status = AsyncMock()
        
        # First event fails, second succeeds
        call_count = 0
        async def mock_find_event_id(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Test error")
            return None
        
        service.event_source_repo.find_event_id_by_source_external = mock_find_event_id
        service.event_source_repo.upsert = AsyncMock()
        
        mock_event = MagicMock()
        mock_event.id = uuid4()
        service.event_repo.create = AsyncMock(return_value=mock_event)
        
        # Mock dedup service - no cross-source match
        service.dedup_service.find_matching_event = AsyncMock(return_value=None)
        
        # Create two events
        events = [sample_eonet_event, sample_eonet_event]
        
        result = await service.ingest_eonet_events(events, atomic=False)
        
        assert result["created"] == 1
        assert result["failed"] == 1
        assert len(result["errors"] or []) == 1
        assert "Test error" in (result["errors"] or [])[0]


class TestIngestionServiceAtomicMode:
    """Tests for atomic transaction behavior."""

    @pytest.fixture
    def mock_session(self) -> MagicMock:
        """Create a mock async session."""
        return MagicMock()

    @pytest.fixture
    def sample_gdacs_event(self) -> GDACSEvent:
        """Create a sample GDACS event."""
        return GDACSEvent(
            external_id="EQ999",
            event_type="earthquake",
            title="Test Event",
            description="Test",
            lat=0.0,
            lng=0.0,
            country="Test",
            severity="medium",
            population=None,
            start_date=datetime.now(timezone.utc),
            url="https://test.com",
            raw_data={},
        )

    @pytest.mark.asyncio
    async def test_atomic_mode_raises_on_error(
        self, mock_session: MagicMock, sample_gdacs_event: GDACSEvent
    ) -> None:
        """Test atomic mode raises exception on error for rollback."""
        service = IngestionService(mock_session)
        
        # Mock data source repository
        mock_data_source = MagicMock()
        mock_data_source.id = uuid4()
        service.data_source_repo.get_or_create = AsyncMock(return_value=mock_data_source)
        
        # Force an error
        service.event_source_repo.find_event_id_by_source_external = AsyncMock(
            side_effect=Exception("Database error")
        )
        
        with pytest.raises(Exception, match="Database error"):
            await service.ingest_gdacs_events([sample_gdacs_event], atomic=True)


class TestIngestionServiceGeoPrecision:
    """Tests for geo precision handling."""

    @pytest.fixture
    def mock_session(self) -> MagicMock:
        """Create a mock async session."""
        return MagicMock()

    @pytest.mark.asyncio
    async def test_geo_precision_approximate_with_coordinates(
        self, mock_session: MagicMock
    ) -> None:
        """Test geo_precision is approximate when coordinates are present."""
        event_with_coords = RawEvent(
            source_name="USGS",
            external_id="test123",
            title="Test Event",
            start_date=datetime.now(timezone.utc),
            lat=35.0,
            lng=135.0,
            event_type_raw="earthquake",
            raw_data={},
        )
        
        service = IngestionService(mock_session)
        
        mock_data_source = MagicMock()
        mock_data_source.id = uuid4()
        service.data_source_repo.get_or_create = AsyncMock(return_value=mock_data_source)
        service.data_source_repo.update_sync_status = AsyncMock()
        service.event_source_repo.find_event_id_by_source_external = AsyncMock(return_value=None)
        service.event_source_repo.upsert = AsyncMock()
        
        mock_event = MagicMock()
        mock_event.id = uuid4()
        service.event_repo.create = AsyncMock(return_value=mock_event)
        
        # Mock dedup service - no cross-source match
        service.dedup_service.find_matching_event = AsyncMock(return_value=None)
        
        await service.ingest_usgs_events([event_with_coords])
        
        call_kwargs = service.event_repo.create.call_args.kwargs
        assert call_kwargs["geo_precision"] == GeoPrecision.approximate

    @pytest.mark.asyncio
    async def test_geo_precision_unknown_without_coordinates(
        self, mock_session: MagicMock
    ) -> None:
        """Test geo_precision is unknown when coordinates are absent."""
        event_no_coords = RawEvent(
            source_name="USGS",
            external_id="test456",
            title="Test Event No Coords",
            start_date=datetime.now(timezone.utc),
            lat=None,
            lng=None,
            event_type_raw="earthquake",
            raw_data={},
        )
        
        service = IngestionService(mock_session)
        
        mock_data_source = MagicMock()
        mock_data_source.id = uuid4()
        service.data_source_repo.get_or_create = AsyncMock(return_value=mock_data_source)
        service.data_source_repo.update_sync_status = AsyncMock()
        service.event_source_repo.find_event_id_by_source_external = AsyncMock(return_value=None)
        service.event_source_repo.upsert = AsyncMock()
        
        mock_event = MagicMock()
        mock_event.id = uuid4()
        service.event_repo.create = AsyncMock(return_value=mock_event)
        
        # Mock dedup service - no cross-source match
        service.dedup_service.find_matching_event = AsyncMock(return_value=None)
        
        await service.ingest_usgs_events([event_no_coords])
        
        call_kwargs = service.event_repo.create.call_args.kwargs
        assert call_kwargs["geo_precision"] == GeoPrecision.unknown
