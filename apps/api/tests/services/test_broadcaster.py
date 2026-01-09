"""Tests for WebSocket broadcaster service."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from src.services.broadcaster import (
    ConnectionManager,
    EventBroadcaster,
)


class TestConnectionManager:
    """Tests for ConnectionManager."""
    
    @pytest.fixture
    def manager(self):
        return ConnectionManager()
    
    @pytest.mark.asyncio
    async def test_connect_adds_websocket(self, manager):
        """Should add websocket to active connections."""
        ws = AsyncMock()
        await manager.connect(ws)
        
        ws.accept.assert_called_once()
        assert manager.connection_count == 1
    
    @pytest.mark.asyncio
    async def test_disconnect_removes_websocket(self, manager):
        """Should remove websocket from active connections."""
        ws = AsyncMock()
        await manager.connect(ws)
        await manager.disconnect(ws)
        
        assert manager.connection_count == 0
    
    @pytest.mark.asyncio
    async def test_broadcast_sends_to_all(self, manager):
        """Should send message to all connected clients."""
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        await manager.connect(ws1)
        await manager.connect(ws2)
        
        await manager.broadcast({"type": "test", "data": "hello"})
        
        assert ws1.send_text.call_count == 1
        assert ws2.send_text.call_count == 1
    
    @pytest.mark.asyncio
    async def test_broadcast_handles_failed_connection(self, manager):
        """Should remove failed connections during broadcast."""
        ws_good = AsyncMock()
        ws_bad = AsyncMock()
        ws_bad.send_text.side_effect = Exception("Connection lost")
        
        await manager.connect(ws_good)
        await manager.connect(ws_bad)
        assert manager.connection_count == 2
        
        await manager.broadcast({"type": "test"})
        
        # Bad connection should be removed
        assert manager.connection_count == 1
    
    @pytest.mark.asyncio
    async def test_broadcast_empty_connections(self, manager):
        """Should handle broadcast with no connections."""
        # Should not raise
        await manager.broadcast({"type": "test"})


class TestEventBroadcaster:
    """Tests for EventBroadcaster."""
    
    @pytest.fixture
    def manager(self):
        return ConnectionManager()
    
    @pytest.fixture
    def broadcaster(self, manager):
        return EventBroadcaster(manager)
    
    @pytest.mark.asyncio
    async def test_broadcast_event_created(self, broadcaster, manager):
        """Should broadcast event_created message."""
        ws = AsyncMock()
        await manager.connect(ws)
        
        event_id = uuid4()
        await broadcaster.broadcast_event_created(
            event_id=event_id,
            event_type="earthquake",
            title="M 6.5 Earthquake",
            severity="high",
            lat=35.0,
            lng=139.0,
            source_name="USGS",
        )
        
        ws.send_text.assert_called_once()
        call_arg = ws.send_text.call_args[0][0]
        import json
        message = json.loads(call_arg)
        
        assert message["type"] == "event_created"
        assert message["data"]["event_id"] == str(event_id)
        assert message["data"]["event_type"] == "earthquake"
        assert message["data"]["source"] == "USGS"
    
    @pytest.mark.asyncio
    async def test_broadcast_event_updated(self, broadcaster, manager):
        """Should broadcast event_updated message."""
        ws = AsyncMock()
        await manager.connect(ws)
        
        event_id = uuid4()
        await broadcaster.broadcast_event_updated(
            event_id=event_id,
            updated_fields=["title", "severity"],
            source_name="GDACS",
        )
        
        ws.send_text.assert_called_once()
        call_arg = ws.send_text.call_args[0][0]
        import json
        message = json.loads(call_arg)
        
        assert message["type"] == "event_updated"
        assert message["data"]["updated_fields"] == ["title", "severity"]
    
    @pytest.mark.asyncio
    async def test_broadcast_event_merged(self, broadcaster, manager):
        """Should broadcast event_merged message."""
        ws = AsyncMock()
        await manager.connect(ws)
        
        event_id = uuid4()
        await broadcaster.broadcast_event_merged(
            event_id=event_id,
            merged_from_source="EONET",
            match_method="fuzzy",
        )
        
        ws.send_text.assert_called_once()
        call_arg = ws.send_text.call_args[0][0]
        import json
        message = json.loads(call_arg)
        
        assert message["type"] == "event_merged"
        assert message["data"]["match_method"] == "fuzzy"
