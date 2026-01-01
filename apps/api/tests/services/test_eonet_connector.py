"""
Tests for the EONETConnector with HTTP mocking.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.core.exceptions import ExternalAPIError
from src.services.connectors.eonet_connector import (
    BASE_URL,
    DEFAULT_TIMEOUT,
    EONET_CATEGORY_MAP,
    MAX_RETRIES,
    EONETConnector,
    EONETEvent,
)


# Sample EONET GeoJSON response for testing
SAMPLE_EONET_GEOJSON = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "id": "EONET_6789",
            "properties": {
                "id": "EONET_6789",
                "title": "Wildfire - California, United States",
                "description": "Fire in northern California affecting multiple counties",
                "link": "https://eonet.gsfc.nasa.gov/api/v3/events/EONET_6789",
                "closed": None,
                "categories": [{"id": "wildfires", "title": "Wildfires"}],
                "sources": [
                    {"id": "InciWeb", "url": "https://inciweb.nwcg.gov/incident/123"},
                    {"id": "CALFIRE", "url": "https://www.fire.ca.gov/incident/456"},
                ],
                "geometryDates": ["2025-01-10T14:30:00Z"],
            },
            "geometry": {
                "type": "Point",
                "coordinates": [-120.5, 38.8],  # [lon, lat]
            },
        },
        {
            "type": "Feature",
            "id": "EONET_1234",
            "properties": {
                "id": "EONET_1234",
                "title": "Severe Storm - Texas, United States",
                "description": None,
                "link": "https://eonet.gsfc.nasa.gov/api/v3/events/EONET_1234",
                "closed": "2025-01-08T00:00:00Z",
                "categories": [{"id": "severeStorms", "title": "Severe Storms"}],
                "sources": [{"id": "NWS", "url": "https://www.weather.gov/storm/456"}],
                "geometryDates": ["2025-01-05T08:00:00Z"],
            },
            "geometry": {
                "type": "Point",
                "coordinates": [-97.5, 31.2],
            },
        },
    ],
}


@pytest.fixture
def sample_eonet_geojson() -> dict:
    """Return sample EONET GeoJSON data."""
    return SAMPLE_EONET_GEOJSON.copy()


@pytest.fixture
def eonet_connector() -> EONETConnector:
    """Create an EONETConnector instance for testing."""
    return EONETConnector()


class TestEONETEventDataclass:
    """Tests for the EONETEvent dataclass."""

    def test_event_creation(self) -> None:
        """Test creating an EONETEvent instance."""
        now = datetime.now(timezone.utc)
        event = EONETEvent(
            event_id="EONET_1234",
            title="Test Wildfire",
            description="A test wildfire event",
            link="https://eonet.gsfc.nasa.gov/api/v3/events/EONET_1234",
            closed=None,
            categories=["wildfires"],
            sources=[{"id": "InciWeb", "url": "https://example.com"}],
            latitude=38.8,
            longitude=-120.5,
            geometry_date=now,
            raw_data={"test": "data"},
        )

        assert event.event_id == "EONET_1234"
        assert event.title == "Test Wildfire"
        assert event.description == "A test wildfire event"
        assert event.closed is None
        assert event.categories == ["wildfires"]
        assert event.latitude == 38.8
        assert event.longitude == -120.5

    def test_event_with_closed_date(self) -> None:
        """Test event with closed date (ended event)."""
        closed_time = datetime(2025, 1, 10, 12, 0, 0, tzinfo=timezone.utc)
        geom_time = datetime(2025, 1, 5, 8, 0, 0, tzinfo=timezone.utc)
        event = EONETEvent(
            event_id="EONET_5678",
            title="Past Event",
            description=None,
            link="",
            closed=closed_time,
            categories=["floods"],
            sources=[],
            latitude=0.0,
            longitude=0.0,
            geometry_date=geom_time,
            raw_data={},
        )

        assert event.closed == closed_time
        assert event.geometry_date == geom_time

    def test_event_multiple_categories(self) -> None:
        """Test event with multiple categories."""
        now = datetime.now(timezone.utc)
        event = EONETEvent(
            event_id="test",
            title="Test",
            description=None,
            link="",
            closed=None,
            categories=["wildfires", "dustHaze"],
            sources=[],
            latitude=0.0,
            longitude=0.0,
            geometry_date=now,
            raw_data={},
        )

        assert len(event.categories) == 2
        assert "wildfires" in event.categories
        assert "dustHaze" in event.categories


class TestEONETConnectorConfiguration:
    """Tests for EONETConnector configuration."""

    def test_default_configuration(self) -> None:
        """Test default connector configuration."""
        connector = EONETConnector()
        assert connector.status == "open"
        assert connector.days == 30
        assert connector.categories is None
        assert connector.timeout == DEFAULT_TIMEOUT
        assert connector.max_retries == MAX_RETRIES

    def test_custom_status(self) -> None:
        """Test connector with custom status."""
        connector = EONETConnector(status="closed")
        assert connector.status == "closed"

        connector = EONETConnector(status="all")
        assert connector.status == "all"

    def test_custom_days(self) -> None:
        """Test connector with custom days."""
        connector = EONETConnector(days=7)
        assert connector.days == 7

    def test_custom_categories(self) -> None:
        """Test connector with category filter."""
        connector = EONETConnector(categories=["wildfires", "volcanoes"])
        assert connector.categories == ["wildfires", "volcanoes"]

    def test_custom_timeout(self) -> None:
        """Test connector with custom timeout."""
        connector = EONETConnector(timeout=60.0)
        assert connector.timeout == 60.0

    def test_custom_max_retries(self) -> None:
        """Test connector with custom max retries."""
        connector = EONETConnector(max_retries=5)
        assert connector.max_retries == 5

    def test_source_name(self) -> None:
        """Test source name is set correctly."""
        connector = EONETConnector()
        assert connector.source_name == "EONET"


class TestEONETConnectorCoordinateExtraction:
    """Tests for geometry coordinate extraction."""

    def test_extract_point_coordinates(self, eonet_connector: EONETConnector) -> None:
        """Test extracting coordinates from Point geometry."""
        geometry = {"type": "Point", "coordinates": [-120.5, 38.8]}
        coords = eonet_connector._extract_coordinates(geometry)

        assert coords is not None
        assert coords[0] == pytest.approx(38.8, rel=0.0001)  # latitude
        assert coords[1] == pytest.approx(-120.5, rel=0.0001)  # longitude

    def test_extract_multipoint_coordinates(
        self, eonet_connector: EONETConnector
    ) -> None:
        """Test extracting coordinates from MultiPoint geometry."""
        geometry = {
            "type": "MultiPoint",
            "coordinates": [
                [-120.5, 38.8],
                [-121.0, 39.0],
                [-119.5, 38.5],
            ],
        }
        coords = eonet_connector._extract_coordinates(geometry)

        assert coords is not None
        # Should use first point
        assert coords[0] == pytest.approx(38.8, rel=0.0001)
        assert coords[1] == pytest.approx(-120.5, rel=0.0001)

    def test_extract_polygon_coordinates(self, eonet_connector: EONETConnector) -> None:
        """Test extracting coordinates from Polygon geometry."""
        geometry = {
            "type": "Polygon",
            "coordinates": [
                [
                    [-120.5, 38.8],
                    [-121.0, 38.8],
                    [-121.0, 39.2],
                    [-120.5, 39.2],
                    [-120.5, 38.8],
                ]
            ],
        }
        coords = eonet_connector._extract_coordinates(geometry)

        assert coords is not None
        # Should use first point of outer ring
        assert coords[0] == pytest.approx(38.8, rel=0.0001)
        assert coords[1] == pytest.approx(-120.5, rel=0.0001)

    def test_extract_linestring_coordinates(
        self, eonet_connector: EONETConnector
    ) -> None:
        """Test extracting coordinates from LineString geometry."""
        geometry = {
            "type": "LineString",
            "coordinates": [
                [-120.5, 38.8],
                [-121.0, 39.0],
            ],
        }
        coords = eonet_connector._extract_coordinates(geometry)

        assert coords is not None
        # Should use first point
        assert coords[0] == pytest.approx(38.8, rel=0.0001)
        assert coords[1] == pytest.approx(-120.5, rel=0.0001)

    def test_extract_empty_coordinates(self, eonet_connector: EONETConnector) -> None:
        """Test handling empty coordinates."""
        geometry = {"type": "Point", "coordinates": []}
        coords = eonet_connector._extract_coordinates(geometry)
        assert coords is None

    def test_extract_missing_geometry(self, eonet_connector: EONETConnector) -> None:
        """Test handling missing geometry type."""
        geometry = {"coordinates": [-120.5, 38.8]}
        coords = eonet_connector._extract_coordinates(geometry)
        assert coords is None

    def test_extract_unknown_geometry_type(
        self, eonet_connector: EONETConnector
    ) -> None:
        """Test handling unknown geometry type."""
        geometry = {"type": "GeometryCollection", "coordinates": []}
        coords = eonet_connector._extract_coordinates(geometry)
        assert coords is None


class TestEONETConnectorParsing:
    """Tests for EONET GeoJSON parsing."""

    def test_parse_feature_valid(self, eonet_connector: EONETConnector) -> None:
        """Test parsing a valid GeoJSON feature."""
        feature = SAMPLE_EONET_GEOJSON["features"][0]
        event = eonet_connector._parse_feature(feature)

        assert event is not None
        assert event.event_id == "EONET_6789"
        assert event.title == "Wildfire - California, United States"
        assert event.description == "Fire in northern California affecting multiple counties"
        assert event.link == "https://eonet.gsfc.nasa.gov/api/v3/events/EONET_6789"
        assert event.closed is None
        assert event.categories == ["wildfires"]
        assert len(event.sources) == 2
        assert event.latitude == pytest.approx(38.8, rel=0.0001)
        assert event.longitude == pytest.approx(-120.5, rel=0.0001)

    def test_parse_feature_with_closed_date(
        self, eonet_connector: EONETConnector
    ) -> None:
        """Test parsing feature with closed date."""
        feature = SAMPLE_EONET_GEOJSON["features"][1]
        event = eonet_connector._parse_feature(feature)

        assert event is not None
        assert event.closed is not None
        assert event.closed.year == 2025
        assert event.closed.month == 1
        assert event.closed.day == 8
        assert event.description is None

    def test_parse_feature_missing_id(self, eonet_connector: EONETConnector) -> None:
        """Test parsing feature with missing ID returns None."""
        feature = {
            "properties": {"title": "Test"},
            "geometry": {"type": "Point", "coordinates": [0, 0]},
        }
        event = eonet_connector._parse_feature(feature)
        assert event is None

    def test_parse_feature_missing_coordinates(
        self, eonet_connector: EONETConnector
    ) -> None:
        """Test parsing feature with missing coordinates returns None."""
        feature = {
            "id": "test",
            "properties": {"id": "test", "title": "Test"},
            "geometry": {"type": "Point", "coordinates": []},
        }
        event = eonet_connector._parse_feature(feature)
        assert event is None

    def test_parse_feature_id_from_feature_level(
        self, eonet_connector: EONETConnector
    ) -> None:
        """Test parsing feature where ID is at feature level, not properties."""
        feature = {
            "id": "EONET_9999",
            "properties": {
                "title": "Test Event",
                "categories": [{"id": "floods"}],
                "sources": [],
                "geometryDates": ["2025-01-01T00:00:00Z"],
            },
            "geometry": {"type": "Point", "coordinates": [100.0, 10.0]},
        }
        event = eonet_connector._parse_feature(feature)

        assert event is not None
        assert event.event_id == "EONET_9999"

    def test_parse_feature_missing_title(self, eonet_connector: EONETConnector) -> None:
        """Test parsing feature with missing title defaults to event ID."""
        feature = {
            "id": "EONET_1111",
            "properties": {
                "id": "EONET_1111",
                "categories": [],
                "sources": [],
                "geometryDates": [],
            },
            "geometry": {"type": "Point", "coordinates": [0, 0]},
        }
        event = eonet_connector._parse_feature(feature)

        assert event is not None
        assert event.title == "EONET Event EONET_1111"

    def test_parse_feature_empty_categories(
        self, eonet_connector: EONETConnector
    ) -> None:
        """Test parsing feature with empty categories."""
        feature = {
            "id": "test",
            "properties": {
                "id": "test",
                "title": "Test",
                "categories": [],
                "sources": [],
                "geometryDates": ["2025-01-01T00:00:00Z"],
            },
            "geometry": {"type": "Point", "coordinates": [0, 0]},
        }
        event = eonet_connector._parse_feature(feature)

        assert event is not None
        assert event.categories == []

    def test_parse_feature_multipoint_geometry(
        self, eonet_connector: EONETConnector
    ) -> None:
        """Test parsing feature with MultiPoint geometry."""
        feature = {
            "id": "EONET_MP",
            "properties": {
                "id": "EONET_MP",
                "title": "MultiPoint Event",
                "categories": [{"id": "volcanoes"}],
                "sources": [],
                "geometryDates": ["2025-01-01T00:00:00Z"],
            },
            "geometry": {
                "type": "MultiPoint",
                "coordinates": [
                    [-155.5, 19.5],  # Hawaii
                    [-155.0, 19.0],
                ],
            },
        }
        event = eonet_connector._parse_feature(feature)

        assert event is not None
        assert event.latitude == pytest.approx(19.5, rel=0.0001)
        assert event.longitude == pytest.approx(-155.5, rel=0.0001)

    def test_parse_feature_polygon_geometry(
        self, eonet_connector: EONETConnector
    ) -> None:
        """Test parsing feature with Polygon geometry."""
        feature = {
            "id": "EONET_POLY",
            "properties": {
                "id": "EONET_POLY",
                "title": "Polygon Event",
                "categories": [{"id": "floods"}],
                "sources": [],
                "geometryDates": ["2025-01-01T00:00:00Z"],
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [-95.0, 30.0],
                        [-94.0, 30.0],
                        [-94.0, 31.0],
                        [-95.0, 31.0],
                        [-95.0, 30.0],
                    ]
                ],
            },
        }
        event = eonet_connector._parse_feature(feature)

        assert event is not None
        # Should use first point of outer ring
        assert event.latitude == pytest.approx(30.0, rel=0.0001)
        assert event.longitude == pytest.approx(-95.0, rel=0.0001)


class TestEONETConnectorCategoryMapping:
    """Tests for category to EventType mapping."""

    def test_category_mapping_completeness(self) -> None:
        """Test all expected categories are mapped."""
        expected_categories = [
            "drought",
            "earthquakes",
            "floods",
            "landslides",
            "manmade",
            "severeStorms",
            "snow",
            "tempExtremes",
            "volcanoes",
            "wildfires",
            "dustHaze",
            "seaLakeIce",
            "waterColor",
        ]

        for category in expected_categories:
            assert category in EONET_CATEGORY_MAP, f"Missing mapping for {category}"

    def test_category_mapping_values(self) -> None:
        """Test specific category mappings."""
        assert EONET_CATEGORY_MAP["wildfires"] == "wildfire"
        assert EONET_CATEGORY_MAP["earthquakes"] == "earthquake"
        assert EONET_CATEGORY_MAP["volcanoes"] == "volcano"
        assert EONET_CATEGORY_MAP["floods"] == "flood"
        assert EONET_CATEGORY_MAP["severeStorms"] == "storm"
        assert EONET_CATEGORY_MAP["landslides"] == "landslide"
        assert EONET_CATEGORY_MAP["drought"] == "drought"
        assert EONET_CATEGORY_MAP["tempExtremes"] == "heatwave"
        assert EONET_CATEGORY_MAP["manmade"] == "industrial"
        assert EONET_CATEGORY_MAP["dustHaze"] == "pollution"

    @pytest.mark.asyncio
    async def test_category_mapping_in_fetch_events(
        self, eonet_connector: EONETConnector, sample_eonet_geojson: dict
    ) -> None:
        """Test category mapping is applied when fetching events."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_eonet_geojson
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            events = await eonet_connector.fetch_events()

            # First event is a wildfire
            assert events[0].event_type_raw == "wildfire"
            # Second event is a severe storm
            assert events[1].event_type_raw == "storm"


class TestEONETConnectorFetchEONETEvents:
    """Tests for fetching EONET events."""

    @pytest.fixture
    def eonet_connector_fast(self) -> EONETConnector:
        """Create an EONETConnector with minimal retries for faster tests."""
        return EONETConnector(timeout=1.0, max_retries=2)

    @pytest.mark.asyncio
    async def test_fetch_eonet_events_success(
        self, eonet_connector: EONETConnector, sample_eonet_geojson: dict
    ) -> None:
        """Test successful EONET event fetch."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_eonet_geojson
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            events = await eonet_connector.fetch_eonet_events()

            assert len(events) == 2
            assert all(isinstance(e, EONETEvent) for e in events)
            mock_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_eonet_events_empty_response(
        self, eonet_connector: EONETConnector
    ) -> None:
        """Test handling empty event response."""
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

            events = await eonet_connector.fetch_eonet_events()
            assert events == []

    @pytest.mark.asyncio
    async def test_fetch_eonet_events_http_error(
        self, eonet_connector: EONETConnector
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
                await eonet_connector.fetch_eonet_events()

            assert exc_info.value.service_name == "EONET"
            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_fetch_eonet_events_with_categories_filter(self) -> None:
        """Test fetching with category filter."""
        connector = EONETConnector(categories=["wildfires", "volcanoes"])

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

            await connector.fetch_eonet_events()

            # Check that categories were included in params
            call_args = mock_client.get.call_args
            params = call_args.kwargs.get("params", {})
            assert params.get("category") == "wildfires,volcanoes"


class TestEONETConnectorFetchEvents:
    """Tests for fetching events (Connector protocol)."""

    @pytest.mark.asyncio
    async def test_fetch_events_returns_raw_events(
        self, eonet_connector: EONETConnector, sample_eonet_geojson: dict
    ) -> None:
        """Test fetch_events returns RawEvent instances."""
        from src.services.connectors.base import RawEvent

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_eonet_geojson
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            events = await eonet_connector.fetch_events()

            assert len(events) == 2
            assert all(isinstance(e, RawEvent) for e in events)

    @pytest.mark.asyncio
    async def test_fetch_events_correct_mapping(
        self, eonet_connector: EONETConnector, sample_eonet_geojson: dict
    ) -> None:
        """Test RawEvent mapping is correct."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_eonet_geojson
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            events = await eonet_connector.fetch_events()

            # Check first event (wildfire)
            event = events[0]
            assert event.source_name == "EONET"
            assert event.external_id == "EONET_6789"
            assert event.title == "Wildfire - California, United States"
            assert event.event_type_raw == "wildfire"
            assert event.lat == pytest.approx(38.8, rel=0.0001)
            assert event.lng == pytest.approx(-120.5, rel=0.0001)
            assert event.source_url == "https://eonet.gsfc.nasa.gov/api/v3/events/EONET_6789"
            assert event.end_date is None  # Ongoing event

            # Check description includes source info
            assert "Fire in northern California" in event.description
            assert "Sources:" in event.description
            assert "InciWeb" in event.description

    @pytest.mark.asyncio
    async def test_fetch_events_with_closed_event(
        self, eonet_connector: EONETConnector, sample_eonet_geojson: dict
    ) -> None:
        """Test handling closed events with end_date."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_eonet_geojson
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            events = await eonet_connector.fetch_events()

            # Second event is closed
            event = events[1]
            assert event.end_date is not None
            assert event.end_date.year == 2025
            assert event.end_date.month == 1
            assert event.end_date.day == 8

    @pytest.mark.asyncio
    async def test_fetch_events_without_description(
        self, eonet_connector: EONETConnector, sample_eonet_geojson: dict
    ) -> None:
        """Test handling events without description."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_eonet_geojson
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            events = await eonet_connector.fetch_events()

            # Second event has no description but has sources
            event = events[1]
            assert event.description is not None
            assert "Sources: NWS" in event.description

    @pytest.mark.asyncio
    async def test_fetch_events_unknown_category(
        self, eonet_connector: EONETConnector
    ) -> None:
        """Test handling unknown categories defaults to 'other'."""
        geojson = {
            "type": "FeatureCollection",
            "features": [
                {
                    "id": "test",
                    "properties": {
                        "id": "test",
                        "title": "Unknown Event",
                        "categories": [{"id": "unknownCategory"}],
                        "sources": [],
                        "geometryDates": ["2025-01-01T00:00:00Z"],
                    },
                    "geometry": {"type": "Point", "coordinates": [0, 0]},
                }
            ],
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = geojson
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            events = await eonet_connector.fetch_events()

            assert len(events) == 1
            assert events[0].event_type_raw == "other"

    @pytest.mark.asyncio
    async def test_fetch_events_no_category(
        self, eonet_connector: EONETConnector
    ) -> None:
        """Test handling events with no categories."""
        geojson = {
            "type": "FeatureCollection",
            "features": [
                {
                    "id": "test",
                    "properties": {
                        "id": "test",
                        "title": "No Category Event",
                        "categories": [],
                        "sources": [],
                        "geometryDates": ["2025-01-01T00:00:00Z"],
                    },
                    "geometry": {"type": "Point", "coordinates": [0, 0]},
                }
            ],
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = geojson
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            events = await eonet_connector.fetch_events()

            assert len(events) == 1
            assert events[0].event_type_raw == "other"


class TestEONETConnectorRetryLogic:
    """Tests for retry logic."""

    @pytest.fixture
    def eonet_connector_fast(self) -> EONETConnector:
        """Create an EONETConnector with minimal retries for faster tests."""
        return EONETConnector(timeout=1.0, max_retries=2)

    @pytest.mark.asyncio
    async def test_retry_on_timeout(
        self, eonet_connector_fast: EONETConnector, sample_eonet_geojson: dict
    ) -> None:
        """Test retries on timeout then succeeds."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_eonet_geojson
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
                events = await eonet_connector_fast.fetch_eonet_events()

            assert len(events) == 2
            assert call_count == 2

    @pytest.mark.asyncio
    async def test_retry_on_503_status(
        self, eonet_connector_fast: EONETConnector, sample_eonet_geojson: dict
    ) -> None:
        """Test retries on 503 Service Unavailable."""
        success_response = MagicMock()
        success_response.status_code = 200
        success_response.json.return_value = sample_eonet_geojson
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
                events = await eonet_connector_fast.fetch_eonet_events()

            assert len(events) == 2
            assert call_count == 2

    @pytest.mark.asyncio
    async def test_retry_on_connection_error(
        self, eonet_connector_fast: EONETConnector, sample_eonet_geojson: dict
    ) -> None:
        """Test retries on connection error."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_eonet_geojson
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
                events = await eonet_connector_fast.fetch_eonet_events()

            assert len(events) == 2
            assert call_count == 2

    @pytest.mark.asyncio
    async def test_exhausted_retries_raises_error(
        self, eonet_connector_fast: EONETConnector
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
                    await eonet_connector_fast.fetch_eonet_events()

            assert exc_info.value.service_name == "EONET"
            assert "after 3 attempts" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_exponential_backoff_timing(
        self, eonet_connector_fast: EONETConnector
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
                    await eonet_connector_fast.fetch_eonet_events()

            # With max_retries=2: initial=1.0, then 2.0
            assert len(sleep_calls) == 2
            assert sleep_calls[0] == pytest.approx(1.0, rel=0.1)
            assert sleep_calls[1] == pytest.approx(2.0, rel=0.1)


class TestEONETConnectorProtocolCompliance:
    """Tests for Connector protocol compliance."""

    def test_implements_connector_protocol(self) -> None:
        """Test EONETConnector implements Connector protocol."""
        from src.services.connectors.base import Connector

        connector = EONETConnector()
        assert isinstance(connector, Connector)

    def test_has_source_name(self) -> None:
        """Test EONETConnector has source_name attribute."""
        connector = EONETConnector()
        assert hasattr(connector, "source_name")
        assert connector.source_name == "EONET"

    def test_has_fetch_events_method(self) -> None:
        """Test EONETConnector has fetch_events method."""
        connector = EONETConnector()
        assert hasattr(connector, "fetch_events")
        assert callable(connector.fetch_events)


class TestEONETConnectorAPIParameters:
    """Tests for API request parameters."""

    @pytest.mark.asyncio
    async def test_default_parameters(self, eonet_connector: EONETConnector) -> None:
        """Test default API parameters are sent correctly."""
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

            await eonet_connector.fetch_eonet_events()

            call_args = mock_client.get.call_args
            url = call_args.args[0]
            params = call_args.kwargs.get("params", {})

            assert url == f"{BASE_URL}/events/geojson"
            assert params["status"] == "open"
            assert params["days"] == "30"
            assert "category" not in params

    @pytest.mark.asyncio
    async def test_custom_parameters(self) -> None:
        """Test custom API parameters are sent correctly."""
        connector = EONETConnector(
            status="all",
            days=7,
            categories=["wildfires", "volcanoes"],
        )

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

            await connector.fetch_eonet_events()

            call_args = mock_client.get.call_args
            params = call_args.kwargs.get("params", {})

            assert params["status"] == "all"
            assert params["days"] == "7"
            assert params["category"] == "wildfires,volcanoes"
