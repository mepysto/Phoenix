"""Tests for Admin API endpoints."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport

from src.main import app
from src.db.database import get_db
from src.core.config import settings

AUTH_HEADERS = {"X-API-Key": settings.api_sync_key}


class TestAdminAuth:
    """Admin endpoints must require the operator API key."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("method", "path"),
        [
            ("get", "/api/v1/admin/status"),
            ("post", "/api/v1/admin/sync/trigger"),
            ("post", "/api/v1/admin/merge/trigger?dry_run=false"),
            ("get", "/scheduler/status"),
        ],
    )
    @pytest.mark.parametrize("headers", [{}, {"X-API-Key": "wrong-key"}])
    async def test_rejects_missing_or_wrong_key(self, method, path, headers):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test", headers=headers
        ) as client:
            response = await getattr(client, method)(path)
        assert response.status_code == 401


class TestAdminStatus:
    """Tests for /api/v1/admin/status endpoint."""
    
    @pytest.mark.asyncio
    async def test_admin_status(self):
        """Should return system status."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers=AUTH_HEADERS,
        ) as client:
            response = await client.get("/api/v1/admin/status")
        
        assert response.status_code == 200
        data = response.json()
        assert "websocket" in data
        assert "scheduler" in data
        assert "active_connections" in data["websocket"]


class TestDedupStatus:
    """Tests for /api/v1/admin/dedup/status endpoint."""
    
    @pytest.mark.asyncio
    async def test_dedup_status_returns_stats(self):
        """Should return deduplication statistics."""
        mock_session = AsyncMock()
        mock_session.execute.side_effect = [
            MagicMock(scalar_one=lambda: 100),
            MagicMock(scalar_one=lambda: 150),
            MagicMock(scalar_one=lambda: 20),
            MagicMock(all=lambda: [("GDACS", 50), ("USGS", 100)]),
        ]
        
        async def mock_get_db():
            yield mock_session
        
        app.dependency_overrides[get_db] = mock_get_db
        
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
                headers=AUTH_HEADERS,
            ) as client:
                response = await client.get("/api/v1/admin/dedup/status")
            
            assert response.status_code == 200
            data = response.json()
            assert "total_events" in data
            assert "total_event_sources" in data
            assert "multi_source_events" in data
            assert "dedup_ratio" in data
            assert "events_by_source" in data
            assert data["total_events"] == 100
            assert data["total_event_sources"] == 150
        finally:
            app.dependency_overrides.clear()


class TestSyncTrigger:
    """Tests for /api/v1/admin/sync/trigger endpoint."""
    
    @pytest.mark.asyncio
    async def test_trigger_single_source(self):
        """Should trigger sync for single source."""
        with patch("src.api.v1.admin.scheduler_service"):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
                headers=AUTH_HEADERS,
            ) as client:
                response = await client.post(
                    "/api/v1/admin/sync/trigger",
                    params={"source": "gdacs"}
                )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "triggered"
        assert data["source"] == "gdacs"
    
    @pytest.mark.asyncio
    async def test_trigger_all_sources(self):
        """Should trigger sync for all sources."""
        with patch("src.api.v1.admin.scheduler_service"):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
                headers=AUTH_HEADERS,
            ) as client:
                response = await client.post("/api/v1/admin/sync/trigger")
        
        assert response.status_code == 200
        data = response.json()
        assert data["source"] == "all"
    
    @pytest.mark.asyncio
    async def test_trigger_invalid_source(self):
        """Should reject invalid source name."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers=AUTH_HEADERS,
        ) as client:
            response = await client.post(
                "/api/v1/admin/sync/trigger",
                params={"source": "invalid"}
            )
        
        assert response.status_code == 400
