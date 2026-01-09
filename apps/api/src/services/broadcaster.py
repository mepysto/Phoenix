"""WebSocket broadcaster for real-time event updates."""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manage WebSocket connections."""

    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        """Accept and track a new connection."""
        await websocket.accept()
        async with self._lock:
            self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total: {len(self.active_connections)}")

    async def disconnect(self, websocket: WebSocket) -> None:
        """Remove a connection."""
        async with self._lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, message: dict[str, Any]) -> None:
        """Send message to all connected clients."""
        if not self.active_connections:
            return

        message_json = json.dumps(message, default=str)
        disconnected: list[WebSocket] = []

        async with self._lock:
            for connection in self.active_connections:
                try:
                    await connection.send_text(message_json)
                except Exception as e:
                    logger.warning(f"Failed to send to client: {e}")
                    disconnected.append(connection)

        # Clean up failed connections
        for conn in disconnected:
            await self.disconnect(conn)

    @property
    def connection_count(self) -> int:
        """Return the number of active connections."""
        return len(self.active_connections)


class EventBroadcaster:
    """Broadcast event updates to WebSocket clients."""

    def __init__(self, manager: ConnectionManager) -> None:
        self.manager = manager

    async def broadcast_event_created(
        self,
        event_id: UUID,
        event_type: str,
        title: str,
        severity: str,
        lat: float | None,
        lng: float | None,
        source_name: str,
    ) -> None:
        """Broadcast new event creation."""
        await self.manager.broadcast({
            "type": "event_created",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": {
                "event_id": str(event_id),
                "event_type": event_type,
                "title": title,
                "severity": severity,
                "lat": lat,
                "lng": lng,
                "source": source_name,
            },
        })

    async def broadcast_event_updated(
        self,
        event_id: UUID,
        updated_fields: list[str],
        source_name: str,
    ) -> None:
        """Broadcast event update."""
        await self.manager.broadcast({
            "type": "event_updated",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": {
                "event_id": str(event_id),
                "updated_fields": updated_fields,
                "source": source_name,
            },
        })

    async def broadcast_event_merged(
        self,
        event_id: UUID,
        merged_from_source: str,
        match_method: str,
    ) -> None:
        """Broadcast event merge (cross-source dedup)."""
        await self.manager.broadcast({
            "type": "event_merged",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": {
                "event_id": str(event_id),
                "merged_from": merged_from_source,
                "match_method": match_method,
            },
        })


# Global instances
connection_manager = ConnectionManager()
event_broadcaster = EventBroadcaster(connection_manager)
