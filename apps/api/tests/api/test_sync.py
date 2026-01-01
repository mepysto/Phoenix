"""
Tests for the Sync API endpoints.
"""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.services.connectors.base import RawEvent
from src.services.gdacs_service import GDACSEvent
from src.services.copernicus_service import CopernicusEvent


class TestSyncGDACS:
    """Tests for POST /api/v1/sync/gdacs endpoint."""

    def test_sync_gdacs_without_api_key(self, client: TestClient) -> None:
        """Test GDACS sync without API key returns 401."""
        response = client.post("/api/v1/sync/gdacs")
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid API key"

    def test_sync_gdacs_with_invalid_api_key(self, client: TestClient) -> None:
        """Test GDACS sync with invalid API key returns 401."""
        response = client.post(
            "/api/v1/sync/gdacs", headers={"X-API-Key": "wrong-key"}
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid API key"

    def test_sync_gdacs_with_valid_api_key(
        self, client: TestClient, api_sync_key: str
    ) -> None:
        """Test GDACS sync with valid API key succeeds."""
        mock_events = [
            GDACSEvent(
                external_id="EQ001",
                event_type="earthquake",
                title="Test Earthquake",
                description="Test description",
                lat=35.0,
                lng=135.0,
                country="Japan",
                severity="high",
                population=10000,
                start_date=datetime.now(timezone.utc),
                url="https://gdacs.org/test",
                raw_data={},
            )
        ]
        mock_ingestion_result = {
            "created": 1,
            "updated": 0,
            "failed": 0,
            "errors": [],
        }

        with patch("src.api.v1.sync.GDACSService") as mock_gdacs_class, \
             patch("src.api.v1.sync.IngestionService") as mock_ingestion_class:
            mock_gdacs = mock_gdacs_class.return_value
            mock_gdacs.fetch_rss_events = AsyncMock(return_value=mock_events)

            mock_ingestion = mock_ingestion_class.return_value
            mock_ingestion.ingest_gdacs_events = AsyncMock(
                return_value=mock_ingestion_result
            )

            response = client.post(
                "/api/v1/sync/gdacs", headers={"X-API-Key": api_sync_key}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["result"]["created"] == 1
            assert data["result"]["updated"] == 0
            assert data["result"]["failed"] == 0


class TestSyncCopernicus:
    """Tests for POST /api/v1/sync/copernicus endpoint."""

    def test_sync_copernicus_without_api_key(self, client: TestClient) -> None:
        """Test Copernicus sync without API key returns 401."""
        response = client.post("/api/v1/sync/copernicus")
        assert response.status_code == 401

    def test_sync_copernicus_with_valid_api_key(
        self, client: TestClient, api_sync_key: str
    ) -> None:
        """Test Copernicus sync with valid API key succeeds."""
        mock_events = [
            CopernicusEvent(
                external_id="EMSR001",
                event_type="flood",
                title="Test Flood",
                description="Test description",
                lat=45.0,
                lng=10.0,
                country="Italy",
                severity="high",
                n_aois=5,
                n_products=10,
                start_date=datetime.now(timezone.utc),
                url="https://copernicus.eu/test",
                raw_data={},
            )
        ]
        mock_ingestion_result = {
            "created": 1,
            "updated": 0,
            "failed": 0,
            "errors": [],
        }

        with patch("src.api.v1.sync.CopernicusEMSService") as mock_copernicus_class, \
             patch("src.api.v1.sync.IngestionService") as mock_ingestion_class:
            mock_copernicus = mock_copernicus_class.return_value
            mock_copernicus.fetch_activations = AsyncMock(return_value=mock_events)

            mock_ingestion = mock_ingestion_class.return_value
            mock_ingestion.ingest_copernicus_events = AsyncMock(
                return_value=mock_ingestion_result
            )

            response = client.post(
                "/api/v1/sync/copernicus", headers={"X-API-Key": api_sync_key}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["result"]["created"] == 1
            assert data["result"]["updated"] == 0
            assert data["result"]["failed"] == 0


class TestSyncUSGS:
    """Tests for POST /api/v1/sync/usgs endpoint."""

    def test_sync_usgs_without_api_key(self, client: TestClient) -> None:
        """Test USGS sync without API key returns 401."""
        response = client.post("/api/v1/sync/usgs")
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid API key"

    def test_sync_usgs_with_invalid_api_key(self, client: TestClient) -> None:
        """Test USGS sync with invalid API key returns 401."""
        response = client.post(
            "/api/v1/sync/usgs", headers={"X-API-Key": "wrong-key"}
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid API key"

    def test_sync_usgs_with_valid_api_key(
        self, client: TestClient, api_sync_key: str
    ) -> None:
        """Test USGS sync with valid API key succeeds."""
        mock_events = [
            RawEvent(
                source_name="USGS",
                external_id="us7000abc123",
                title="M 5.5 - 100km NW of Tokyo, Japan",
                description="Test earthquake",
                start_date=datetime.now(timezone.utc),
                source_url="https://earthquake.usgs.gov/earthquakes/eventpage/us7000abc123",
                lat=35.0,
                lng=135.0,
                event_type_raw="earthquake",
                magnitude=5.5,
                raw_data={},
            )
        ]
        mock_ingestion_result = {
            "created": 1,
            "updated": 0,
            "failed": 0,
            "errors": [],
        }

        with patch("src.api.v1.sync.USGSConnector") as mock_usgs_class, \
             patch("src.api.v1.sync.IngestionService") as mock_ingestion_class:
            mock_usgs = mock_usgs_class.return_value
            mock_usgs.fetch_events = AsyncMock(return_value=mock_events)

            mock_ingestion = mock_ingestion_class.return_value
            mock_ingestion.ingest_usgs_events = AsyncMock(
                return_value=mock_ingestion_result
            )

            response = client.post(
                "/api/v1/sync/usgs", headers={"X-API-Key": api_sync_key}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["result"]["created"] == 1
            assert data["result"]["updated"] == 0
            assert data["result"]["failed"] == 0

    def test_sync_usgs_with_custom_feed(
        self, client: TestClient, api_sync_key: str
    ) -> None:
        """Test USGS sync with custom feed parameter."""
        mock_events: list[RawEvent] = []
        mock_ingestion_result = {
            "created": 0,
            "updated": 0,
            "failed": 0,
            "errors": [],
        }

        with patch("src.api.v1.sync.USGSConnector") as mock_usgs_class, \
             patch("src.api.v1.sync.IngestionService") as mock_ingestion_class:
            mock_usgs = mock_usgs_class.return_value
            mock_usgs.fetch_events = AsyncMock(return_value=mock_events)

            mock_ingestion = mock_ingestion_class.return_value
            mock_ingestion.ingest_usgs_events = AsyncMock(
                return_value=mock_ingestion_result
            )

            response = client.post(
                "/api/v1/sync/usgs?feed=significant_month",
                headers={"X-API-Key": api_sync_key}
            )
            assert response.status_code == 200
            
            # Verify the connector was created with the custom feed
            mock_usgs_class.assert_called_once_with(feed="significant_month")


class TestSyncEONET:
    """Tests for POST /api/v1/sync/eonet endpoint."""

    def test_sync_eonet_without_api_key(self, client: TestClient) -> None:
        """Test EONET sync without API key returns 401."""
        response = client.post("/api/v1/sync/eonet")
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid API key"

    def test_sync_eonet_with_invalid_api_key(self, client: TestClient) -> None:
        """Test EONET sync with invalid API key returns 401."""
        response = client.post(
            "/api/v1/sync/eonet", headers={"X-API-Key": "wrong-key"}
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid API key"

    def test_sync_eonet_with_valid_api_key(
        self, client: TestClient, api_sync_key: str
    ) -> None:
        """Test EONET sync with valid API key succeeds."""
        mock_events = [
            RawEvent(
                source_name="EONET",
                external_id="EONET_6789",
                title="Wildfire - California, United States",
                description="Active wildfire",
                start_date=datetime.now(timezone.utc),
                source_url="https://eonet.gsfc.nasa.gov/api/v3/events/EONET_6789",
                lat=38.5816,
                lng=-121.4944,
                event_type_raw="wildfire",
                raw_data={},
            )
        ]
        mock_ingestion_result = {
            "created": 1,
            "updated": 0,
            "failed": 0,
            "errors": [],
        }

        with patch("src.api.v1.sync.EONETConnector") as mock_eonet_class, \
             patch("src.api.v1.sync.IngestionService") as mock_ingestion_class:
            mock_eonet = mock_eonet_class.return_value
            mock_eonet.fetch_events = AsyncMock(return_value=mock_events)

            mock_ingestion = mock_ingestion_class.return_value
            mock_ingestion.ingest_eonet_events = AsyncMock(
                return_value=mock_ingestion_result
            )

            response = client.post(
                "/api/v1/sync/eonet", headers={"X-API-Key": api_sync_key}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["result"]["created"] == 1
            assert data["result"]["updated"] == 0
            assert data["result"]["failed"] == 0

    def test_sync_eonet_with_custom_params(
        self, client: TestClient, api_sync_key: str
    ) -> None:
        """Test EONET sync with custom status and days parameters."""
        mock_events: list[RawEvent] = []
        mock_ingestion_result = {
            "created": 0,
            "updated": 0,
            "failed": 0,
            "errors": [],
        }

        with patch("src.api.v1.sync.EONETConnector") as mock_eonet_class, \
             patch("src.api.v1.sync.IngestionService") as mock_ingestion_class:
            mock_eonet = mock_eonet_class.return_value
            mock_eonet.fetch_events = AsyncMock(return_value=mock_events)

            mock_ingestion = mock_ingestion_class.return_value
            mock_ingestion.ingest_eonet_events = AsyncMock(
                return_value=mock_ingestion_result
            )

            response = client.post(
                "/api/v1/sync/eonet?status=all&days=60",
                headers={"X-API-Key": api_sync_key}
            )
            assert response.status_code == 200
            
            # Verify the connector was created with custom parameters
            mock_eonet_class.assert_called_once_with(status="all", days=60)

    def test_sync_eonet_days_validation(
        self, client: TestClient, api_sync_key: str
    ) -> None:
        """Test EONET sync validates days parameter range."""
        # Days > 365 should fail validation
        response = client.post(
            "/api/v1/sync/eonet?days=400",
            headers={"X-API-Key": api_sync_key}
        )
        assert response.status_code == 422  # Validation error

        # Days < 1 should fail validation
        response = client.post(
            "/api/v1/sync/eonet?days=0",
            headers={"X-API-Key": api_sync_key}
        )
        assert response.status_code == 422  # Validation error


class TestSyncApiKeyValidation:
    """Tests for API key validation in sync endpoints."""

    def test_empty_api_key(self, client: TestClient) -> None:
        """Test sync with empty API key returns 401."""
        response = client.post("/api/v1/sync/gdacs", headers={"X-API-Key": ""})
        assert response.status_code == 401

    def test_case_sensitive_api_key(
        self, client: TestClient, api_sync_key: str
    ) -> None:
        """Test API key validation is case-sensitive."""
        response = client.post(
            "/api/v1/sync/gdacs",
            headers={"X-API-Key": api_sync_key.upper()},
        )
        # Should fail if key case doesn't match
        if api_sync_key != api_sync_key.upper():
            assert response.status_code == 401

    def test_all_sync_endpoints_require_api_key(self, client: TestClient) -> None:
        """Test all sync endpoints require API key."""
        endpoints = [
            "/api/v1/sync/gdacs",
            "/api/v1/sync/copernicus",
            "/api/v1/sync/usgs",
            "/api/v1/sync/eonet",
        ]
        
        for endpoint in endpoints:
            response = client.post(endpoint)
            assert response.status_code == 401, f"Endpoint {endpoint} should require API key"
