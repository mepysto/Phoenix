"""
Tests for the USGSConnector with HTTP mocking.
"""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.core.exceptions import ExternalAPIError
from src.services.connectors.usgs_connector import (
    DEFAULT_TIMEOUT,
    MAX_RETRIES,
    USGS_FEEDS,
    USGSConnector,
    USGSEarthquake,
)


# Sample USGS GeoJSON response for testing
SAMPLE_USGS_GEOJSON = {
    "type": "FeatureCollection",
    "metadata": {
        "generated": 1735660800000,
        "title": "USGS Earthquakes",
        "count": 2,
    },
    "features": [
        {
            "type": "Feature",
            "id": "us7000rlps",
            "properties": {
                "mag": 5.2,
                "place": "161 km NNW of Tobelo, Indonesia",
                "time": 1735660000000,  # 2024-12-31 12:26:40 UTC
                "url": "https://earthquake.usgs.gov/earthquakes/eventpage/us7000rlps",
                "title": "M 5.2 - 161 km NNW of Tobelo, Indonesia",
                "alert": "green",
                "tsunami": 0,
                "magType": "mb",
                "type": "earthquake",
            },
            "geometry": {
                "type": "Point",
                "coordinates": [127.7093, 3.1544, 106.207],  # [lon, lat, depth]
            },
        },
        {
            "type": "Feature",
            "id": "nc75115896",
            "properties": {
                "mag": 4.8,
                "place": "10 km SE of The Geysers, CA",
                "time": 1735650000000,
                "url": "https://earthquake.usgs.gov/earthquakes/eventpage/nc75115896",
                "title": "M 4.8 - 10 km SE of The Geysers, CA",
                "alert": "yellow",
                "tsunami": 1,
                "magType": "mw",
                "type": "earthquake",
            },
            "geometry": {
                "type": "Point",
                "coordinates": [-122.7389, 38.7453, 3.05],
            },
        },
    ],
}


@pytest.fixture
def sample_usgs_geojson() -> dict:
    """Return sample USGS GeoJSON data."""
    return SAMPLE_USGS_GEOJSON.copy()


@pytest.fixture
def usgs_connector() -> USGSConnector:
    """Create a USGSConnector instance for testing."""
    return USGSConnector(feed="4.5_week")


class TestUSGSEarthquakeDataclass:
    """Tests for the USGSEarthquake dataclass."""

    def test_earthquake_creation(self) -> None:
        """Test creating a USGSEarthquake instance."""
        now = datetime.now(timezone.utc)
        eq = USGSEarthquake(
            event_id="us7000test",
            title="M 5.0 - Test Location",
            place="Test Location",
            magnitude=5.0,
            mag_type="mb",
            latitude=35.0,
            longitude=139.0,
            depth_km=10.5,
            time=now,
            url="https://earthquake.usgs.gov/eventpage/us7000test",
            alert="green",
            tsunami=False,
            raw_data={"test": "data"},
        )

        assert eq.event_id == "us7000test"
        assert eq.magnitude == 5.0
        assert eq.latitude == 35.0
        assert eq.longitude == 139.0
        assert eq.alert == "green"
        assert eq.tsunami is False

    def test_earthquake_with_none_alert(self) -> None:
        """Test earthquake with no PAGER alert level."""
        now = datetime.now(timezone.utc)
        eq = USGSEarthquake(
            event_id="test",
            title="Test",
            place="Test",
            magnitude=3.0,
            mag_type="ml",
            latitude=0.0,
            longitude=0.0,
            depth_km=0.0,
            time=now,
            url="",
            alert=None,  # No alert for small earthquakes
            tsunami=False,
            raw_data={},
        )

        assert eq.alert is None


class TestUSGSConnectorConfiguration:
    """Tests for USGSConnector configuration."""

    def test_default_configuration(self) -> None:
        """Test default connector configuration."""
        connector = USGSConnector()
        assert connector.feed == "4.5_week"
        assert connector.timeout == DEFAULT_TIMEOUT
        assert connector.max_retries == MAX_RETRIES
        assert connector.feed_url == USGS_FEEDS["4.5_week"]

    def test_custom_feed(self) -> None:
        """Test connector with custom feed."""
        connector = USGSConnector(feed="significant_month")
        assert connector.feed == "significant_month"
        assert connector.feed_url == USGS_FEEDS["significant_month"]

    def test_custom_timeout(self) -> None:
        """Test connector with custom timeout."""
        connector = USGSConnector(timeout=60.0)
        assert connector.timeout == 60.0

    def test_custom_max_retries(self) -> None:
        """Test connector with custom max retries."""
        connector = USGSConnector(max_retries=5)
        assert connector.max_retries == 5

    def test_invalid_feed_raises_error(self) -> None:
        """Test that invalid feed name raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            USGSConnector(feed="invalid_feed")

        assert "Unknown feed: invalid_feed" in str(exc_info.value)
        assert "4.5_week" in str(exc_info.value)

    def test_source_name(self) -> None:
        """Test source name is set correctly."""
        connector = USGSConnector()
        assert connector.source_name == "USGS"

    def test_all_feeds_available(self) -> None:
        """Test all expected feeds are available."""
        expected_feeds = ["4.5_day", "4.5_week", "all_day", "significant_month"]
        for feed in expected_feeds:
            connector = USGSConnector(feed=feed)
            assert connector.feed == feed


class TestUSGSConnectorParsing:
    """Tests for USGS GeoJSON parsing."""

    def test_parse_feature_valid(self, usgs_connector: USGSConnector) -> None:
        """Test parsing a valid GeoJSON feature."""
        feature = SAMPLE_USGS_GEOJSON["features"][0]
        eq = usgs_connector._parse_feature(feature)

        assert eq is not None
        assert eq.event_id == "us7000rlps"
        assert eq.title == "M 5.2 - 161 km NNW of Tobelo, Indonesia"
        assert eq.place == "161 km NNW of Tobelo, Indonesia"
        assert eq.magnitude == 5.2
        assert eq.mag_type == "mb"
        assert eq.longitude == pytest.approx(127.7093, rel=0.0001)
        assert eq.latitude == pytest.approx(3.1544, rel=0.0001)
        assert eq.depth_km == pytest.approx(106.207, rel=0.001)
        assert eq.alert == "green"
        assert eq.tsunami is False
        assert eq.url == "https://earthquake.usgs.gov/earthquakes/eventpage/us7000rlps"

    def test_parse_feature_with_tsunami(self, usgs_connector: USGSConnector) -> None:
        """Test parsing feature with tsunami warning."""
        feature = SAMPLE_USGS_GEOJSON["features"][1]
        eq = usgs_connector._parse_feature(feature)

        assert eq is not None
        assert eq.tsunami is True
        assert eq.alert == "yellow"
        assert eq.mag_type == "mw"

    def test_parse_feature_missing_coordinates(
        self, usgs_connector: USGSConnector
    ) -> None:
        """Test parsing feature with missing coordinates returns None."""
        feature = {
            "id": "test",
            "properties": {"mag": 5.0},
            "geometry": {"type": "Point", "coordinates": []},
        }
        eq = usgs_connector._parse_feature(feature)
        assert eq is None

    def test_parse_feature_missing_id(self, usgs_connector: USGSConnector) -> None:
        """Test parsing feature with missing ID returns None."""
        feature = {
            "properties": {"mag": 5.0},
            "geometry": {"type": "Point", "coordinates": [0, 0, 0]},
        }
        eq = usgs_connector._parse_feature(feature)
        assert eq is None

    def test_parse_feature_missing_magnitude(
        self, usgs_connector: USGSConnector
    ) -> None:
        """Test parsing feature with missing magnitude defaults to 0."""
        feature = {
            "id": "test",
            "properties": {"title": "Test Event"},
            "geometry": {"type": "Point", "coordinates": [0, 0, 0]},
        }
        eq = usgs_connector._parse_feature(feature)
        assert eq is not None
        assert eq.magnitude == 0.0

    def test_parse_feature_missing_depth(self, usgs_connector: USGSConnector) -> None:
        """Test parsing feature with only 2D coordinates."""
        feature = {
            "id": "test",
            "properties": {"mag": 5.0, "title": "Test"},
            "geometry": {"type": "Point", "coordinates": [100.0, 10.0]},  # No depth
        }
        eq = usgs_connector._parse_feature(feature)
        assert eq is not None
        assert eq.depth_km == 0.0

    def test_parse_feature_missing_place(self, usgs_connector: USGSConnector) -> None:
        """Test parsing feature with missing place defaults to 'Unknown location'."""
        feature = {
            "id": "test",
            "properties": {"mag": 5.0, "title": "Test"},
            "geometry": {"type": "Point", "coordinates": [0, 0, 0]},
        }
        eq = usgs_connector._parse_feature(feature)
        assert eq is not None
        assert eq.place == "Unknown location"

    def test_parse_feature_null_alert(self, usgs_connector: USGSConnector) -> None:
        """Test parsing feature with null alert level."""
        feature = {
            "id": "test",
            "properties": {"mag": 5.0, "title": "Test", "alert": None},
            "geometry": {"type": "Point", "coordinates": [0, 0, 0]},
        }
        eq = usgs_connector._parse_feature(feature)
        assert eq is not None
        assert eq.alert is None


class TestUSGSConnectorFetchEarthquakes:
    """Tests for fetching earthquakes."""

    @pytest.fixture
    def usgs_connector_fast(self) -> USGSConnector:
        """Create a USGSConnector with minimal retries for faster tests."""
        return USGSConnector(timeout=1.0, max_retries=2)

    @pytest.mark.asyncio
    async def test_fetch_earthquakes_success(
        self, usgs_connector: USGSConnector, sample_usgs_geojson: dict
    ) -> None:
        """Test successful earthquake fetch."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_usgs_geojson
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            earthquakes = await usgs_connector.fetch_earthquakes()

            assert len(earthquakes) == 2
            assert all(isinstance(eq, USGSEarthquake) for eq in earthquakes)
            mock_client.get.assert_called_once_with(USGS_FEEDS["4.5_week"])

    @pytest.mark.asyncio
    async def test_fetch_earthquakes_empty_response(
        self, usgs_connector: USGSConnector
    ) -> None:
        """Test handling empty earthquake response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"type": "FeatureCollection", "features": []}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            earthquakes = await usgs_connector.fetch_earthquakes()
            assert earthquakes == []

    @pytest.mark.asyncio
    async def test_fetch_earthquakes_http_error(
        self, usgs_connector: USGSConnector
    ) -> None:
        """Test handling HTTP errors."""
        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(
                side_effect=httpx.HTTPStatusError(
                    "Not Found", request=MagicMock(), response=mock_response
                )
            )
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            with pytest.raises(ExternalAPIError) as exc_info:
                await usgs_connector.fetch_earthquakes()

            assert exc_info.value.service_name == "USGS"
            assert exc_info.value.status_code == 404


class TestUSGSConnectorFetchEvents:
    """Tests for fetching events (Connector protocol)."""

    @pytest.mark.asyncio
    async def test_fetch_events_returns_raw_events(
        self, usgs_connector: USGSConnector, sample_usgs_geojson: dict
    ) -> None:
        """Test fetch_events returns RawEvent instances."""
        from src.services.connectors.base import RawEvent

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_usgs_geojson
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            events = await usgs_connector.fetch_events()

            assert len(events) == 2
            assert all(isinstance(e, RawEvent) for e in events)

    @pytest.mark.asyncio
    async def test_fetch_events_correct_mapping(
        self, usgs_connector: USGSConnector, sample_usgs_geojson: dict
    ) -> None:
        """Test RawEvent mapping is correct."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_usgs_geojson
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            events = await usgs_connector.fetch_events()

            # Check first event
            event = events[0]
            assert event.source_name == "USGS"
            assert event.external_id == "us7000rlps"
            assert event.title == "M 5.2 - 161 km NNW of Tobelo, Indonesia"
            assert event.event_type_raw == "earthquake"
            assert event.severity_raw == "green"
            assert event.magnitude == 5.2
            assert event.lat == pytest.approx(3.1544, rel=0.0001)
            assert event.lng == pytest.approx(127.7093, rel=0.0001)
            assert "Magnitude 5.2" in event.description
            assert "Depth:" in event.description

    @pytest.mark.asyncio
    async def test_fetch_events_tsunami_description(
        self, usgs_connector: USGSConnector, sample_usgs_geojson: dict
    ) -> None:
        """Test tsunami warning is included in description."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_usgs_geojson
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            events = await usgs_connector.fetch_events()

            # Second event has tsunami warning
            event = events[1]
            assert "Tsunami warning issued" in event.description


class TestUSGSConnectorRetryLogic:
    """Tests for retry logic."""

    @pytest.fixture
    def usgs_connector_fast(self) -> USGSConnector:
        """Create a USGSConnector with minimal retries for faster tests."""
        return USGSConnector(timeout=1.0, max_retries=2)

    @pytest.mark.asyncio
    async def test_retry_on_timeout(
        self, usgs_connector_fast: USGSConnector, sample_usgs_geojson: dict
    ) -> None:
        """Test retries on timeout then succeeds."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_usgs_geojson
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
                earthquakes = await usgs_connector_fast.fetch_earthquakes()

            assert len(earthquakes) == 2
            assert call_count == 2

    @pytest.mark.asyncio
    async def test_retry_on_503_status(
        self, usgs_connector_fast: USGSConnector, sample_usgs_geojson: dict
    ) -> None:
        """Test retries on 503 Service Unavailable."""
        success_response = MagicMock()
        success_response.status_code = 200
        success_response.json.return_value = sample_usgs_geojson
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
                earthquakes = await usgs_connector_fast.fetch_earthquakes()

            assert len(earthquakes) == 2
            assert call_count == 2

    @pytest.mark.asyncio
    async def test_retry_on_connection_error(
        self, usgs_connector_fast: USGSConnector, sample_usgs_geojson: dict
    ) -> None:
        """Test retries on connection error."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_usgs_geojson
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
                earthquakes = await usgs_connector_fast.fetch_earthquakes()

            assert len(earthquakes) == 2
            assert call_count == 2

    @pytest.mark.asyncio
    async def test_exhausted_retries_raises_error(
        self, usgs_connector_fast: USGSConnector
    ) -> None:
        """Test ExternalAPIError is raised when all retries exhausted."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            with patch("asyncio.sleep", new_callable=AsyncMock):
                with pytest.raises(ExternalAPIError) as exc_info:
                    await usgs_connector_fast.fetch_earthquakes()

            assert exc_info.value.service_name == "USGS"
            assert "after 3 attempts" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_exponential_backoff_timing(
        self, usgs_connector_fast: USGSConnector
    ) -> None:
        """Test exponential backoff uses correct delays."""
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
                    await usgs_connector_fast.fetch_earthquakes()

            # With max_retries=2: initial=1.0, then 2.0
            assert len(sleep_calls) == 2
            assert sleep_calls[0] == pytest.approx(1.0, rel=0.1)
            assert sleep_calls[1] == pytest.approx(2.0, rel=0.1)


class TestUSGSConnectorProtocolCompliance:
    """Tests for Connector protocol compliance."""

    def test_implements_connector_protocol(self) -> None:
        """Test USGSConnector implements Connector protocol."""
        from src.services.connectors.base import Connector

        connector = USGSConnector()
        assert isinstance(connector, Connector)

    def test_has_source_name(self) -> None:
        """Test USGSConnector has source_name attribute."""
        connector = USGSConnector()
        assert hasattr(connector, "source_name")
        assert connector.source_name == "USGS"

    def test_has_fetch_events_method(self) -> None:
        """Test USGSConnector has fetch_events method."""
        connector = USGSConnector()
        assert hasattr(connector, "fetch_events")
        assert callable(connector.fetch_events)


class TestUSGSConnectorDescriptionBuilding:
    """Tests for description building."""

    def test_build_description_basic(self, usgs_connector: USGSConnector) -> None:
        """Test basic description building."""
        eq = USGSEarthquake(
            event_id="test",
            title="Test",
            place="Test Location",
            magnitude=5.5,
            mag_type="mb",
            latitude=0.0,
            longitude=0.0,
            depth_km=10.0,
            time=datetime.now(timezone.utc),
            url="",
            alert=None,
            tsunami=False,
            raw_data={},
        )

        desc = usgs_connector._build_description(eq)
        assert "Magnitude 5.5 mb earthquake" in desc
        assert "Depth: 10.0 km" in desc
        assert "Location: Test Location" in desc

    def test_build_description_with_tsunami(
        self, usgs_connector: USGSConnector
    ) -> None:
        """Test description includes tsunami warning."""
        eq = USGSEarthquake(
            event_id="test",
            title="Test",
            place="Test Location",
            magnitude=7.0,
            mag_type="mw",
            latitude=0.0,
            longitude=0.0,
            depth_km=50.0,
            time=datetime.now(timezone.utc),
            url="",
            alert="red",
            tsunami=True,
            raw_data={},
        )

        desc = usgs_connector._build_description(eq)
        assert "Tsunami warning issued" in desc

    def test_build_description_no_mag_type(
        self, usgs_connector: USGSConnector
    ) -> None:
        """Test description without magnitude type."""
        eq = USGSEarthquake(
            event_id="test",
            title="Test",
            place="Unknown location",
            magnitude=4.0,
            mag_type="",
            latitude=0.0,
            longitude=0.0,
            depth_km=0.0,
            time=datetime.now(timezone.utc),
            url="",
            alert=None,
            tsunami=False,
            raw_data={},
        )

        desc = usgs_connector._build_description(eq)
        assert "Magnitude 4.0 earthquake" in desc
        assert "Unknown location" not in desc  # Should skip unknown location
