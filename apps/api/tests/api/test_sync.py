"""
Tests for the Sync API endpoints.
"""
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient


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
        with patch(
            "src.api.v1.sync.GDACSService"
        ) as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.sync_events = AsyncMock(return_value=5)

            response = client.post(
                "/api/v1/sync/gdacs", headers={"X-API-Key": api_sync_key}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "completed"
            assert data["synced"] == 5


class TestSyncCopernicus:
    """Tests for POST /api/v1/sync/copernicus endpoint."""

    def test_sync_copernicus_without_api_key(self, client: TestClient) -> None:
        """Test Copernicus sync without API key returns 401."""
        response = client.post("/api/v1/sync/copernicus")
        assert response.status_code == 401

    def test_sync_copernicus_with_valid_api_key(
        self, client: TestClient, api_sync_key: str
    ) -> None:
        """Test Copernicus sync returns not_implemented status."""
        response = client.post(
            "/api/v1/sync/copernicus", headers={"X-API-Key": api_sync_key}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "not_implemented"


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
