"""WebSocket broadcaster for real-time event updates."""

import asyncio
import json
import logging
from datetime import datetime, timezone
from collections.abc import Awaitable, Callable
from typing import Any
from uuid import UUID

from fastapi import WebSocket
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

SEND_TIMEOUT_SECONDS = 5.0


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
        # Snapshot under the lock, send outside it: one slow client must not
        # block connects/disconnects or delay delivery to everyone else.
        async with self._lock:
            connections = list(self.active_connections)

        async def send(connection: WebSocket) -> WebSocket | None:
            try:
                await asyncio.wait_for(connection.send_text(message_json), SEND_TIMEOUT_SECONDS)
                return None
            except Exception as e:  # timeout or closed socket
                logger.warning(f"Failed to send to client: {e!r}")
                return connection

        failed = await asyncio.gather(*(send(c) for c in connections))
        for conn in failed:
            if conn is not None:
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


# ---------------------------------------------------------------------------
# Transaction-aware delivery
# ---------------------------------------------------------------------------

BroadcastSend = Callable[[], Awaitable[None]]
_PENDING_KEY = "phoenix_pending_broadcasts"
# Strong references so fire-and-forget tasks are not garbage-collected mid-send
_inflight: set[asyncio.Task[None]] = set()


def broadcast_after_commit(session: AsyncSession, send: BroadcastSend) -> None:
    """Deliver `send()` only once the session's transaction commits.

    Clients must never be told about rows that are later rolled back. On
    rollback the queued broadcasts are discarded.
    """
    sync_session = getattr(session, "sync_session", None)
    if not isinstance(sync_session, Session):
        # Not a real session (unit tests with mocks): nothing will ever commit
        return
    sync_session.info.setdefault(_PENDING_KEY, []).append(send)


@event.listens_for(Session, "after_commit")
def _deliver_pending(session: Session) -> None:
    # after_commit also fires when a SAVEPOINT is released; only the outermost
    # commit makes the rows visible to other connections.
    if session.in_nested_transaction():
        return
    pending: list[BroadcastSend] = session.info.pop(_PENDING_KEY, [])
    if not pending:
        return
    loop = asyncio.get_running_loop()
    for send in pending:
        task = loop.create_task(send())
        _inflight.add(task)
        task.add_done_callback(_inflight.discard)


@event.listens_for(Session, "after_soft_rollback")
def _discard_pending(session: Session, previous_transaction: Any) -> None:
    # A savepoint rollback (one failed event in a batch) must not drop the
    # broadcasts of events that already succeeded; only the outermost does.
    if previous_transaction.parent is None:
        session.info.pop(_PENDING_KEY, None)
