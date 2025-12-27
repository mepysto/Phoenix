"""
Tests for the GDACSService with HTTP mocking.
"""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
import httpx

from src.core.exceptions import DataSyncError, ExternalAPIError
from src.services.gdacs_service import (
    GDACSService,
    GDACSEvent,
    GDACS_EVENT_TYPE_MAP,
    GDACS_SEVERITY_MAP,
    DEFAULT_TIMEOUT,
    MAX_RETRIES,
)


class TestGDACSServiceRSSParsing:
    """Tests for GDACS RSS feed parsing."""

    @pytest.fixture
    def gdacs_service(self) -> GDACSService:
        """Create a GDACSService instance for testing."""
        return GDACSService()

    def test_parse_rss_valid_xml(
        self, gdacs_service: GDACSService, sample_gdacs_rss_xml: str
    ) -> None:
        """Test parsing valid RSS XML returns events."""
        events = gdacs_service._parse_rss(sample_gdacs_rss_xml)

        assert len(events) == 2
        assert all(isinstance(e, GDACSEvent) for e in events)

    def test_parse_rss_extracts_event_type(
        self, gdacs_service: GDACSService, sample_gdacs_rss_xml: str
    ) -> None:
        """Test RSS parsing extracts correct event types."""
        events = gdacs_service._parse_rss(sample_gdacs_rss_xml)

        assert events[0].event_type == "earthquake"
        assert events[1].event_type == "flood"

    def test_parse_rss_extracts_severity(
        self, gdacs_service: GDACSService, sample_gdacs_rss_xml: str
    ) -> None:
        """Test RSS parsing extracts correct severity levels."""
        events = gdacs_service._parse_rss(sample_gdacs_rss_xml)

        assert events[0].severity == "medium"  # Orange -> medium
        assert events[1].severity == "high"  # Red -> high

    def test_parse_rss_extracts_coordinates(
        self, gdacs_service: GDACSService, sample_gdacs_rss_xml: str
    ) -> None:
        """Test RSS parsing extracts correct coordinates."""
        events = gdacs_service._parse_rss(sample_gdacs_rss_xml)

        # First event: Turkey
        assert events[0].lat == pytest.approx(39.9334, rel=0.001)
        assert events[0].lng == pytest.approx(32.8597, rel=0.001)

        # Second event: Bangladesh
        assert events[1].lat == pytest.approx(23.8103, rel=0.001)
        assert events[1].lng == pytest.approx(90.4125, rel=0.001)

    def test_parse_rss_extracts_population(
        self, gdacs_service: GDACSService, sample_gdacs_rss_xml: str
    ) -> None:
        """Test RSS parsing extracts population data."""
        events = gdacs_service._parse_rss(sample_gdacs_rss_xml)

        assert events[0].population == 50000
        assert events[1].population == 200000

    def test_parse_rss_empty_feed(self, gdacs_service: GDACSService) -> None:
        """Test parsing empty RSS feed returns empty list."""
        empty_rss = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0"><channel><title>Empty</title></channel></rss>"""

        events = gdacs_service._parse_rss(empty_rss)
        assert events == []

    def test_parse_rss_missing_coordinates_skips_item(
        self, gdacs_service: GDACSService
    ) -> None:
        """Test items without coordinates are skipped."""
        rss_no_coords = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0" xmlns:gdacs="http://www.gdacs.org">
          <channel>
            <item>
              <title>No Coordinates Event</title>
              <gdacs:eventtype>EQ</gdacs:eventtype>
            </item>
          </channel>
        </rss>"""

        events = gdacs_service._parse_rss(rss_no_coords)
        assert events == []


class TestGDACSServiceFetchRSSEvents:
    """Tests for GDACS RSS fetching with HTTP mocking."""

    @pytest.fixture
    def gdacs_service(self) -> GDACSService:
        """Create a GDACSService instance for testing."""
        return GDACSService()

    @pytest.mark.asyncio
    async def test_fetch_rss_events_success(
        self, gdacs_service: GDACSService, sample_gdacs_rss_xml: str
    ) -> None:
        """Test successful RSS fetch and parse."""
        mock_response = MagicMock()
        mock_response.text = sample_gdacs_rss_xml
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            events = await gdacs_service.fetch_rss_events()

            assert len(events) == 2
            mock_client.get.assert_called_once_with(GDACSService.RSS_URL, params=None)

    @pytest.mark.asyncio
    async def test_fetch_rss_events_http_error_raises_external_api_error(
        self, gdacs_service: GDACSService
    ) -> None:
        """Test RSS fetch handles non-retryable HTTP errors."""
        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(
                side_effect=httpx.HTTPStatusError(
                    "Not Found",
                    request=MagicMock(),
                    response=mock_response,
                )
            )
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            with pytest.raises(ExternalAPIError) as exc_info:
                await gdacs_service.fetch_rss_events()

            assert exc_info.value.service_name == "GDACS"
            assert exc_info.value.status_code == 404


class TestGDACSServiceRetryLogic:
    """Tests for GDACS service retry logic."""

    @pytest.fixture
    def gdacs_service(self) -> GDACSService:
        """Create a GDACSService instance with minimal retries for faster tests."""
        return GDACSService(timeout=1.0, max_retries=2)

    @pytest.mark.asyncio
    async def test_retry_on_timeout(
        self, gdacs_service: GDACSService, sample_gdacs_rss_xml: str
    ) -> None:
        """Test retries on timeout then succeeds."""
        mock_response = MagicMock()
        mock_response.text = sample_gdacs_rss_xml
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        call_count = 0

        async def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise httpx.TimeoutException("Timeout")
            return mock_response

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = mock_get
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            with patch("asyncio.sleep", new_callable=AsyncMock):
                events = await gdacs_service.fetch_rss_events()

            assert len(events) == 2
            assert call_count == 2

    @pytest.mark.asyncio
    async def test_retry_on_connection_error(
        self, gdacs_service: GDACSService, sample_gdacs_rss_xml: str
    ) -> None:
        """Test retries on connection error then succeeds."""
        mock_response = MagicMock()
        mock_response.text = sample_gdacs_rss_xml
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        call_count = 0

        async def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise httpx.ConnectError("Connection refused")
            return mock_response

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = mock_get
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            with patch("asyncio.sleep", new_callable=AsyncMock):
                events = await gdacs_service.fetch_rss_events()

            assert len(events) == 2
            assert call_count == 2

    @pytest.mark.asyncio
    async def test_retry_on_503_status_code(
        self, gdacs_service: GDACSService, sample_gdacs_rss_xml: str
    ) -> None:
        """Test retries on 503 Service Unavailable."""
        success_response = MagicMock()
        success_response.text = sample_gdacs_rss_xml
        success_response.status_code = 200
        success_response.raise_for_status = MagicMock()

        error_response = MagicMock()
        error_response.status_code = 503

        call_count = 0

        async def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                return error_response
            return success_response

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = mock_get
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            with patch("asyncio.sleep", new_callable=AsyncMock):
                events = await gdacs_service.fetch_rss_events()

            assert len(events) == 2
            assert call_count == 2

    @pytest.mark.asyncio
    async def test_exhausted_retries_raises_external_api_error(
        self, gdacs_service: GDACSService
    ) -> None:
        """Test ExternalAPIError is raised when all retries are exhausted."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            with patch("asyncio.sleep", new_callable=AsyncMock):
                with pytest.raises(ExternalAPIError) as exc_info:
                    await gdacs_service.fetch_rss_events()

            assert exc_info.value.service_name == "GDACS"
            assert "after 3 attempts" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_exponential_backoff_timing(
        self, gdacs_service: GDACSService
    ) -> None:
        """Test that exponential backoff uses correct delays."""
        sleep_calls = []

        async def mock_sleep(delay):
            sleep_calls.append(delay)

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            with patch("asyncio.sleep", side_effect=mock_sleep):
                with pytest.raises(ExternalAPIError):
                    await gdacs_service.fetch_rss_events()

            # With max_retries=2: initial=1.0, then 2.0 (multiplier=2.0)
            assert len(sleep_calls) == 2
            assert sleep_calls[0] == pytest.approx(1.0, rel=0.1)
            assert sleep_calls[1] == pytest.approx(2.0, rel=0.1)


class TestGDACSServiceFetchAPIEvents:
    """Tests for GDACS API fetching."""

    @pytest.fixture
    def gdacs_service(self) -> GDACSService:
        """Create a GDACSService instance for testing."""
        return GDACSService()

    @pytest.mark.asyncio
    async def test_fetch_api_events_success(
        self, gdacs_service: GDACSService
    ) -> None:
        """Test successful API fetch."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "features": [
                {"id": 1, "type": "earthquake"},
                {"id": 2, "type": "flood"},
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            events = await gdacs_service.fetch_api_events()

            assert len(events) == 2

    @pytest.mark.asyncio
    async def test_fetch_api_events_with_filters(
        self, gdacs_service: GDACSService
    ) -> None:
        """Test API fetch with filters."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"features": []}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            await gdacs_service.fetch_api_events(
                event_types=["EQ", "FL"],
                from_date="2024-01-01",
                alert_level="Red",
            )

            # Verify params were passed correctly
            call_args = mock_client.get.call_args
            params = call_args.kwargs.get("params", {})
            assert params.get("eventlist") == "EQ,FL"
            assert params.get("fromdate") == "2024-01-01"
            assert params.get("alertlevel") == "Red"


class TestGDACSServiceSyncEvents:
    """Tests for GDACS sync_events method."""

    @pytest.fixture
    def gdacs_service(self) -> GDACSService:
        """Create a GDACSService instance for testing."""
        return GDACSService()

    @pytest.mark.asyncio
    async def test_sync_events_returns_count(
        self, gdacs_service: GDACSService, sample_gdacs_rss_xml: str
    ) -> None:
        """Test sync_events returns correct count."""
        mock_response = MagicMock()
        mock_response.text = sample_gdacs_rss_xml
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            count = await gdacs_service.sync_events()

            assert count == 2

    @pytest.mark.asyncio
    async def test_sync_events_raises_data_sync_error_on_failure(
        self, gdacs_service: GDACSService
    ) -> None:
        """Test sync_events raises DataSyncError when all retries fail."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            with patch("asyncio.sleep", new_callable=AsyncMock):
                with pytest.raises(DataSyncError) as exc_info:
                    await gdacs_service.sync_events()

            assert exc_info.value.source == "GDACS"
            assert exc_info.value.retry_count == MAX_RETRIES


class TestGDACSMappings:
    """Tests for GDACS type and severity mappings."""

    def test_event_type_mapping(self) -> None:
        """Test all expected event types are mapped."""
        expected_mappings = {
            "EQ": "earthquake",
            "FL": "flood",
            "TC": "hurricane",
            "VO": "volcano",
            "DR": "drought",
            "WF": "wildfire",
            "TS": "tsunami",
        }
        for code, event_type in expected_mappings.items():
            assert GDACS_EVENT_TYPE_MAP.get(code) == event_type

    def test_severity_mapping(self) -> None:
        """Test all expected severity levels are mapped."""
        expected_mappings = {
            "Green": "low",
            "Orange": "medium",
            "Red": "high",
        }
        for alert_level, severity in expected_mappings.items():
            assert GDACS_SEVERITY_MAP.get(alert_level) == severity

    def test_unknown_event_type_defaults(self) -> None:
        """Test unknown event type code returns None from map."""
        assert GDACS_EVENT_TYPE_MAP.get("XX") is None

    def test_unknown_severity_defaults(self) -> None:
        """Test unknown severity returns None from map."""
        assert GDACS_SEVERITY_MAP.get("Unknown") is None


class TestGDACSServiceConfiguration:
    """Tests for GDACS service configuration."""

    def test_default_timeout(self) -> None:
        """Test default timeout is set correctly."""
        service = GDACSService()
        assert service.timeout == DEFAULT_TIMEOUT

    def test_default_max_retries(self) -> None:
        """Test default max retries is set correctly."""
        service = GDACSService()
        assert service.max_retries == MAX_RETRIES

    def test_custom_timeout(self) -> None:
        """Test custom timeout can be set."""
        service = GDACSService(timeout=5.0)
        assert service.timeout == 5.0

    def test_custom_max_retries(self) -> None:
        """Test custom max retries can be set."""
        service = GDACSService(max_retries=5)
        assert service.max_retries == 5
