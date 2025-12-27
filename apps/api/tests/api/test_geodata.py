"""
Tests for the GeoData API endpoints.
"""
import pytest
from fastapi.testclient import TestClient


class TestVectorTiles:
    """Tests for GET /api/v1/geodata/tiles/{z}/{x}/{y} endpoint."""

    def test_get_vector_tile_success(self, client: TestClient) -> None:
        """Test getting a vector tile returns proper response."""
        response = client.get("/api/v1/geodata/tiles/10/512/512")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/x-protobuf"

    def test_get_vector_tile_different_zoom_levels(self, client: TestClient) -> None:
        """Test vector tiles at different zoom levels."""
        for z in [0, 5, 10, 15]:
            response = client.get(f"/api/v1/geodata/tiles/{z}/0/0")
            assert response.status_code == 200

    def test_get_vector_tile_invalid_coordinates(self, client: TestClient) -> None:
        """Test vector tile with string coordinates returns 422."""
        response = client.get("/api/v1/geodata/tiles/a/b/c")
        assert response.status_code == 422

    def test_get_vector_tile_returns_empty_content(self, client: TestClient) -> None:
        """Test that vector tile currently returns empty content (placeholder)."""
        response = client.get("/api/v1/geodata/tiles/1/1/1")
        assert response.status_code == 200
        # Current implementation returns empty bytes
        assert response.content == b""
