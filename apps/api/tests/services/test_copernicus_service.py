"""
Tests for the CopernicusEMSService with HTTP mocking.
"""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
import httpx

from src.core.exceptions import DataSyncError, ExternalAPIError
from src.services.copernicus_service import (
    CopernicusEMSService,
    CopernicusEvent,
    COPERNICUS_EVENT_TYPE_MAP,
    COPERNICUS_SEVERITY_THRESHOLDS,
    DEFAULT_TIMEOUT,
    MAX_RETRIES,
    parse_wkt_point,
    calculate_severity,
)


# Mock response data
MOCK_ACTIVATION_RESPONSE = {
    "count": 2,
    "results": [
        {
            "code": "EMSR847",
            "name": "Flood in Valencia, Spain",
            "category": {"name": "Flood", "slug": "flood"},
            "activationTime": "2024-10-29T00:00:00Z",
            "centroid": "POINT(-0.5 39.5)",
            "countries": [{"name": "Spain", "short_name": "ES"}],
            "n_aois": 15,
            "n_products": 30,
            "drmPhase": "response",
        },
        {
            "code": "EMSR848",
            "name": "Wildfire in Portugal",
            "category": {"name": "Wildfire", "slug": "wildfire"},
            "activationTime": "2024-10-30T12:00:00Z",
            "centroid": "POINT(-8.0 40.0)",
            "countries": [{"name": "Portugal", "short_name": "PT"}],
            "n_aois": 3,
            "n_products": 10,
            "drmPhase": "monitoring",
        },
    ],
}

MOCK_RAPID_MAPPING_RESPONSE = [
    {
        "code": "EMSR847",
        "name": "Flood in Valencia, Spain",
        "status": "active",
        "aois": [{"id": 1, "name": "AOI1"}, {"id": 2, "name": "AOI2"}],
    }
]


class TestParseWktPoint:
    """Tests for WKT point parsing utility."""

    def test_parse_valid_point(self) -> None:
        """Test parsing valid WKT POINT format."""
        result = parse_wkt_point("POINT(-0.5 39.5)")
        assert result is not None
        lat, lng = result
        assert lat == pytest.approx(39.5, rel=0.001)
        assert lng == pytest.approx(-0.5, rel=0.001)

    def test_parse_point_with_extra_spaces(self) -> None:
        """Test parsing WKT POINT with extra whitespace."""
        result = parse_wkt_point("POINT(  -0.5   39.5  )")
        assert result is not None
        lat, lng = result
        assert lat == pytest.approx(39.5, rel=0.001)
        assert lng == pytest.approx(-0.5, rel=0.001)

    def test_parse_point_lowercase(self) -> None:
        """Test parsing lowercase WKT POINT."""
        result = parse_wkt_point("point(-8.0 40.0)")
        assert result is not None
        lat, lng = result
        assert lat == pytest.approx(40.0, rel=0.001)
        assert lng == pytest.approx(-8.0, rel=0.001)

    def test_parse_point_positive_coordinates(self) -> None:
        """Test parsing positive coordinates."""
        result = parse_wkt_point("POINT(139.6503 35.6762)")
        assert result is not None
        lat, lng = result
        assert lat == pytest.approx(35.6762, rel=0.001)
        assert lng == pytest.approx(139.6503, rel=0.001)

    def test_parse_empty_string_returns_none(self) -> None:
        """Test parsing empty string returns None."""
        assert parse_wkt_point("") is None

    def test_parse_none_returns_none(self) -> None:
        """Test parsing None returns None."""
        assert parse_wkt_point(None) is None  # type: ignore

    def test_parse_invalid_format_returns_none(self) -> None:
        """Test parsing invalid format returns None."""
        assert parse_wkt_point("INVALID") is None
        assert parse_wkt_point("POLYGON((0 0, 1 1, 1 0, 0 0))") is None
        assert parse_wkt_point("39.5, -0.5") is None


class TestCalculateSeverity:
    """Tests for severity calculation utility."""

    def test_critical_severity(self) -> None:
        """Test n_aois > 10 returns critical."""
        assert calculate_severity(11) == "critical"
        assert calculate_severity(15) == "critical"
        assert calculate_severity(100) == "critical"

    def test_high_severity(self) -> None:
        """Test 5 < n_aois <= 10 returns high."""
        assert calculate_severity(6) == "high"
        assert calculate_severity(10) == "high"

    def test_medium_severity(self) -> None:
        """Test n_aois <= 5 returns medium."""
        assert calculate_severity(5) == "medium"
        assert calculate_severity(3) == "medium"
        assert calculate_severity(0) == "medium"

    def test_threshold_boundaries(self) -> None:
        """Test exact threshold boundaries."""
        # At thresholds
        assert calculate_severity(COPERNICUS_SEVERITY_THRESHOLDS["critical"]) == "high"
        assert calculate_severity(COPERNICUS_SEVERITY_THRESHOLDS["high"]) == "medium"

        # Just above thresholds
        assert calculate_severity(COPERNICUS_SEVERITY_THRESHOLDS["critical"] + 1) == "critical"
        assert calculate_severity(COPERNICUS_SEVERITY_THRESHOLDS["high"] + 1) == "high"


class TestCopernicusEMSServiceParsing:
    """Tests for Copernicus EMS activation parsing."""

    @pytest.fixture
    def copernicus_service(self) -> CopernicusEMSService:
        """Create a CopernicusEMSService instance for testing."""
        return CopernicusEMSService()

    def test_parse_activation_valid(self, copernicus_service: CopernicusEMSService) -> None:
        """Test parsing valid activation data."""
        item = MOCK_ACTIVATION_RESPONSE["results"][0]
        event = copernicus_service._parse_activation(item)

        assert event is not None
        assert event.external_id == "EMSR847"
        assert event.title == "Flood in Valencia, Spain"
        assert event.event_type == "flood"
        assert event.lat == pytest.approx(39.5, rel=0.001)
        assert event.lng == pytest.approx(-0.5, rel=0.001)
        assert event.country == "Spain"
        assert event.n_aois == 15
        assert event.n_products == 30
        assert event.severity == "critical"  # n_aois > 10

    def test_parse_activation_extracts_event_type(
        self, copernicus_service: CopernicusEMSService
    ) -> None:
        """Test parsing extracts correct event types."""
        flood_item = MOCK_ACTIVATION_RESPONSE["results"][0]
        wildfire_item = MOCK_ACTIVATION_RESPONSE["results"][1]

        flood_event = copernicus_service._parse_activation(flood_item)
        wildfire_event = copernicus_service._parse_activation(wildfire_item)

        assert flood_event is not None
        assert wildfire_event is not None
        assert flood_event.event_type == "flood"
        assert wildfire_event.event_type == "wildfire"

    def test_parse_activation_calculates_severity(
        self, copernicus_service: CopernicusEMSService
    ) -> None:
        """Test parsing calculates correct severity based on n_aois."""
        # n_aois = 15 -> critical
        critical_event = copernicus_service._parse_activation(MOCK_ACTIVATION_RESPONSE["results"][0])
        assert critical_event is not None
        assert critical_event.severity == "critical"

        # n_aois = 3 -> medium
        medium_event = copernicus_service._parse_activation(MOCK_ACTIVATION_RESPONSE["results"][1])
        assert medium_event is not None
        assert medium_event.severity == "medium"

    def test_parse_activation_missing_code_returns_none(
        self, copernicus_service: CopernicusEMSService
    ) -> None:
        """Test parsing activation without code returns None."""
        item = {"name": "Test Event", "centroid": "POINT(0 0)"}
        assert copernicus_service._parse_activation(item) is None

    def test_parse_activation_missing_centroid_returns_none(
        self, copernicus_service: CopernicusEMSService
    ) -> None:
        """Test parsing activation without valid centroid returns None."""
        item = {"code": "EMSR999", "name": "Test Event"}
        assert copernicus_service._parse_activation(item) is None

    def test_parse_activation_invalid_centroid_returns_none(
        self, copernicus_service: CopernicusEMSService
    ) -> None:
        """Test parsing activation with invalid centroid returns None."""
        item = {"code": "EMSR999", "name": "Test Event", "centroid": "INVALID"}
        assert copernicus_service._parse_activation(item) is None

    def test_parse_activation_generates_description(
        self, copernicus_service: CopernicusEMSService
    ) -> None:
        """Test parsing generates appropriate description."""
        event = copernicus_service._parse_activation(MOCK_ACTIVATION_RESPONSE["results"][0])

        assert event is not None
        assert "Flood" in event.description
        assert "Spain" in event.description
        assert "response phase" in event.description
        assert "15 areas of interest" in event.description

    def test_parse_activation_generates_url(
        self, copernicus_service: CopernicusEMSService
    ) -> None:
        """Test parsing generates correct URL."""
        event = copernicus_service._parse_activation(MOCK_ACTIVATION_RESPONSE["results"][0])

        assert event is not None
        assert event.url == "https://rapidmapping.emergency.copernicus.eu/EMSR/EMSR847"

    def test_parse_activation_parses_datetime(
        self, copernicus_service: CopernicusEMSService
    ) -> None:
        """Test parsing correctly parses activation time."""
        event = copernicus_service._parse_activation(MOCK_ACTIVATION_RESPONSE["results"][0])

        assert event is not None
        assert event.start_date.year == 2024
        assert event.start_date.month == 10
        assert event.start_date.day == 29

    def test_parse_activation_unknown_category(
        self, copernicus_service: CopernicusEMSService
    ) -> None:
        """Test parsing handles unknown category."""
        item = {
            "code": "EMSR999",
            "name": "Unknown Event",
            "category": {"name": "Unknown", "slug": "unknown-category"},
            "centroid": "POINT(0 0)",
            "countries": [],
            "n_aois": 1,
        }
        event = copernicus_service._parse_activation(item)

        assert event is not None
        assert event.event_type == "other"


class TestCopernicusEMSServiceFetchActivations:
    """Tests for Copernicus EMS fetch activations with HTTP mocking."""

    @pytest.fixture
    def copernicus_service(self) -> CopernicusEMSService:
        """Create a CopernicusEMSService instance for testing."""
        return CopernicusEMSService()

    @pytest.mark.asyncio
    async def test_fetch_activations_success(
        self, copernicus_service: CopernicusEMSService
    ) -> None:
        """Test successful activations fetch and parse."""
        mock_response = MagicMock()
        mock_response.json.return_value = MOCK_ACTIVATION_RESPONSE
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            events = await copernicus_service.fetch_activations()

            assert len(events) == 2
            assert all(isinstance(e, CopernicusEvent) for e in events)
            mock_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_activations_with_limit(
        self, copernicus_service: CopernicusEMSService
    ) -> None:
        """Test fetch activations with custom limit."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"results": []}
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            await copernicus_service.fetch_activations(limit=50)

            call_args = mock_client.get.call_args
            params = call_args.kwargs.get("params", {})
            assert params.get("limit") == "50"

    @pytest.mark.asyncio
    async def test_fetch_activations_with_category(
        self, copernicus_service: CopernicusEMSService
    ) -> None:
        """Test fetch activations with category filter."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"results": []}
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            await copernicus_service.fetch_activations(category="flood")

            call_args = mock_client.get.call_args
            params = call_args.kwargs.get("params", {})
            assert params.get("category__slug") == "flood"

    @pytest.mark.asyncio
    async def test_fetch_activations_http_error_raises_external_api_error(
        self, copernicus_service: CopernicusEMSService
    ) -> None:
        """Test fetch handles non-retryable HTTP errors."""
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
                await copernicus_service.fetch_activations()

            assert exc_info.value.service_name == "Copernicus"
            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_fetch_activations_empty_results(
        self, copernicus_service: CopernicusEMSService
    ) -> None:
        """Test fetch returns empty list when no results."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"results": []}
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            events = await copernicus_service.fetch_activations()

            assert events == []


class TestCopernicusEMSServiceFetchActivationDetails:
    """Tests for Copernicus EMS fetch activation details."""

    @pytest.fixture
    def copernicus_service(self) -> CopernicusEMSService:
        """Create a CopernicusEMSService instance for testing."""
        return CopernicusEMSService()

    @pytest.mark.asyncio
    async def test_fetch_activation_details_success_list_response(
        self, copernicus_service: CopernicusEMSService
    ) -> None:
        """Test successful activation details fetch with list response."""
        mock_response = MagicMock()
        mock_response.json.return_value = MOCK_RAPID_MAPPING_RESPONSE
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            result = await copernicus_service.fetch_activation_details("EMSR847")

            assert result is not None
            assert result["code"] == "EMSR847"

    @pytest.mark.asyncio
    async def test_fetch_activation_details_success_dict_response(
        self, copernicus_service: CopernicusEMSService
    ) -> None:
        """Test successful activation details fetch with dict response."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"code": "EMSR847", "status": "active"}
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            result = await copernicus_service.fetch_activation_details("EMSR847")

            assert result is not None
            assert result["code"] == "EMSR847"

    @pytest.mark.asyncio
    async def test_fetch_activation_details_not_found_returns_none(
        self, copernicus_service: CopernicusEMSService
    ) -> None:
        """Test fetch returns None for 404 response."""
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

            # 404 should raise ExternalAPIError which is caught and returns None
            with patch.object(
                copernicus_service, "_request_with_retry"
            ) as mock_request:
                mock_request.side_effect = ExternalAPIError(
                    message="Not Found",
                    service_name="Copernicus",
                    status_code=404,
                )
                result = await copernicus_service.fetch_activation_details("EMSR999")

            assert result is None

    @pytest.mark.asyncio
    async def test_fetch_activation_details_empty_list_returns_none(
        self, copernicus_service: CopernicusEMSService
    ) -> None:
        """Test fetch returns None for empty list response."""
        mock_response = MagicMock()
        mock_response.json.return_value = []
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            result = await copernicus_service.fetch_activation_details("EMSR847")

            assert result is None


class TestCopernicusEMSServiceRetryLogic:
    """Tests for Copernicus EMS service retry logic."""

    @pytest.fixture
    def copernicus_service(self) -> CopernicusEMSService:
        """Create a CopernicusEMSService instance with minimal retries for faster tests."""
        return CopernicusEMSService(timeout=1.0, max_retries=2)

    @pytest.mark.asyncio
    async def test_retry_on_timeout(
        self, copernicus_service: CopernicusEMSService
    ) -> None:
        """Test retries on timeout then succeeds."""
        mock_response = MagicMock()
        mock_response.json.return_value = MOCK_ACTIVATION_RESPONSE
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
                events = await copernicus_service.fetch_activations()

            assert len(events) == 2
            assert call_count == 2

    @pytest.mark.asyncio
    async def test_retry_on_connection_error(
        self, copernicus_service: CopernicusEMSService
    ) -> None:
        """Test retries on connection error then succeeds."""
        mock_response = MagicMock()
        mock_response.json.return_value = MOCK_ACTIVATION_RESPONSE
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
                events = await copernicus_service.fetch_activations()

            assert len(events) == 2
            assert call_count == 2

    @pytest.mark.asyncio
    async def test_retry_on_503_status_code(
        self, copernicus_service: CopernicusEMSService
    ) -> None:
        """Test retries on 503 Service Unavailable."""
        success_response = MagicMock()
        success_response.json.return_value = MOCK_ACTIVATION_RESPONSE
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
                events = await copernicus_service.fetch_activations()

            assert len(events) == 2
            assert call_count == 2

    @pytest.mark.asyncio
    async def test_retry_on_429_rate_limit(
        self, copernicus_service: CopernicusEMSService
    ) -> None:
        """Test retries on 429 Too Many Requests."""
        success_response = MagicMock()
        success_response.json.return_value = MOCK_ACTIVATION_RESPONSE
        success_response.status_code = 200
        success_response.raise_for_status = MagicMock()

        rate_limit_response = MagicMock()
        rate_limit_response.status_code = 429

        call_count = 0

        async def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                return rate_limit_response
            return success_response

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = mock_get
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            with patch("asyncio.sleep", new_callable=AsyncMock):
                events = await copernicus_service.fetch_activations()

            assert len(events) == 2
            assert call_count == 2

    @pytest.mark.asyncio
    async def test_exhausted_retries_raises_external_api_error(
        self, copernicus_service: CopernicusEMSService
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
                    await copernicus_service.fetch_activations()

            assert exc_info.value.service_name == "Copernicus"
            assert "3 attempts" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_exponential_backoff_timing(
        self, copernicus_service: CopernicusEMSService
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
                    await copernicus_service.fetch_activations()

            # With max_retries=2: initial=1.0, then 2.0 (multiplier=2.0)
            assert len(sleep_calls) == 2
            assert sleep_calls[0] == pytest.approx(1.0, rel=0.1)
            assert sleep_calls[1] == pytest.approx(2.0, rel=0.1)


class TestCopernicusEMSServiceSyncEvents:
    """Tests for Copernicus sync_events method."""

    @pytest.fixture
    def copernicus_service(self) -> CopernicusEMSService:
        """Create a CopernicusEMSService instance for testing."""
        return CopernicusEMSService()

    @pytest.mark.asyncio
    async def test_sync_events_returns_count(
        self, copernicus_service: CopernicusEMSService
    ) -> None:
        """Test sync_events returns correct count."""
        mock_response = MagicMock()
        mock_response.json.return_value = MOCK_ACTIVATION_RESPONSE
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            count = await copernicus_service.sync_events()

            assert count == 2

    @pytest.mark.asyncio
    async def test_sync_events_raises_data_sync_error_on_failure(
        self, copernicus_service: CopernicusEMSService
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
                    await copernicus_service.sync_events()

            assert exc_info.value.source == "Copernicus"
            assert exc_info.value.retry_count == MAX_RETRIES


class TestCopernicusEMSServiceFetchByCategory:
    """Tests for Copernicus EMS fetch by category."""

    @pytest.fixture
    def copernicus_service(self) -> CopernicusEMSService:
        """Create a CopernicusEMSService instance for testing."""
        return CopernicusEMSService()

    @pytest.mark.asyncio
    async def test_fetch_by_category_multiple_categories(
        self, copernicus_service: CopernicusEMSService
    ) -> None:
        """Test fetching by multiple categories deduplicates results."""
        flood_response = {
            "results": [
                {
                    "code": "EMSR847",
                    "name": "Flood in Valencia",
                    "category": {"name": "Flood", "slug": "flood"},
                    "centroid": "POINT(-0.5 39.5)",
                    "countries": [{"name": "Spain"}],
                    "n_aois": 15,
                }
            ]
        }
        wildfire_response = {
            "results": [
                {
                    "code": "EMSR848",
                    "name": "Wildfire in Portugal",
                    "category": {"name": "Wildfire", "slug": "wildfire"},
                    "centroid": "POINT(-8.0 40.0)",
                    "countries": [{"name": "Portugal"}],
                    "n_aois": 3,
                }
            ]
        }

        call_count = 0

        async def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.raise_for_status = MagicMock()

            params = kwargs.get("params", {})
            if params.get("category__slug") == "flood":
                mock_response.json.return_value = flood_response
            else:
                mock_response.json.return_value = wildfire_response

            return mock_response

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = mock_get
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            events = await copernicus_service.fetch_activations_by_category(
                categories=["flood", "wildfire"]
            )

            assert len(events) == 2
            codes = {e.external_id for e in events}
            assert codes == {"EMSR847", "EMSR848"}

    @pytest.mark.asyncio
    async def test_fetch_by_category_no_categories_fetches_all(
        self, copernicus_service: CopernicusEMSService
    ) -> None:
        """Test fetching without categories fetches all activations."""
        mock_response = MagicMock()
        mock_response.json.return_value = MOCK_ACTIVATION_RESPONSE
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            events = await copernicus_service.fetch_activations_by_category(categories=None)

            assert len(events) == 2
            # Should request with higher limit (50 * 4 = 200)
            call_args = mock_client.get.call_args
            params = call_args.kwargs.get("params", {})
            assert params.get("limit") == "200"


class TestCopernicusMappings:
    """Tests for Copernicus type mappings."""

    def test_event_type_mapping(self) -> None:
        """Test all expected event types are mapped."""
        expected_mappings = {
            "flood": "flood",
            "storm": "hurricane",
            "wildfire": "wildfire",
            "earthquake": "earthquake",
            "volcano": "volcano",
            "drought": "drought",
            "landslide": "landslide",
            "tsunami": "tsunami",
            "industrial-accident": "industrial",
            "other": "other",
        }
        for slug, event_type in expected_mappings.items():
            assert COPERNICUS_EVENT_TYPE_MAP.get(slug) == event_type

    def test_severity_thresholds(self) -> None:
        """Test severity thresholds are defined correctly."""
        assert COPERNICUS_SEVERITY_THRESHOLDS["critical"] == 10
        assert COPERNICUS_SEVERITY_THRESHOLDS["high"] == 5

    def test_unknown_category_defaults(self) -> None:
        """Test unknown category returns None from map."""
        assert COPERNICUS_EVENT_TYPE_MAP.get("unknown-category") is None


class TestCopernicusEMSServiceConfiguration:
    """Tests for Copernicus EMS service configuration."""

    def test_default_timeout(self) -> None:
        """Test default timeout is set correctly."""
        service = CopernicusEMSService()
        assert service.timeout == DEFAULT_TIMEOUT

    def test_default_max_retries(self) -> None:
        """Test default max retries is set correctly."""
        service = CopernicusEMSService()
        assert service.max_retries == MAX_RETRIES

    def test_custom_timeout(self) -> None:
        """Test custom timeout can be set."""
        service = CopernicusEMSService(timeout=5.0)
        assert service.timeout == 5.0

    def test_custom_max_retries(self) -> None:
        """Test custom max retries can be set."""
        service = CopernicusEMSService(max_retries=5)
        assert service.max_retries == 5

    def test_service_urls_defined(self) -> None:
        """Test service URLs are defined correctly."""
        assert CopernicusEMSService.ACTIVATIONS_URL.startswith("https://")
        assert CopernicusEMSService.RAPID_MAPPING_URL.startswith("https://")
        assert "copernicus" in CopernicusEMSService.ACTIVATIONS_URL
        assert "copernicus" in CopernicusEMSService.RAPID_MAPPING_URL
