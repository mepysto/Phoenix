"""WebSocket endpoints for real-time updates."""

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from src.services.broadcaster import connection_manager

logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/events")
async def websocket_events(websocket: WebSocket) -> None:
    """WebSocket endpoint for real-time event updates.

    Clients receive:
    - event_created: New event added
    - event_updated: Existing event modified
    - event_merged: Event merged from another source

    Example message:
    {
        "type": "event_created",
        "timestamp": "2024-01-01T12:00:00",
        "data": {
            "event_id": "uuid",
            "event_type": "earthquake",
            "title": "M 6.5 Earthquake",
            "severity": "high",
            "lat": 35.0,
            "lng": 139.0,
            "source": "USGS"
        }
    }
    """
    await connection_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive, handle any client messages
            data = await websocket.receive_text()
            # Could handle ping/pong or subscription filters here
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        await connection_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await connection_manager.disconnect(websocket)
