"""WebSocket endpoint: origin allowlist, connection limit, ping."""

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from src.core.config import settings
from src.services.broadcaster import connection_manager


def test_allowed_origin_connects_and_answers_ping(client: TestClient) -> None:
    origin = settings.cors_origins[0]
    with client.websocket_connect("/ws/events", headers={"origin": origin}) as ws:
        ws.send_text("ping")
        assert ws.receive_text() == "pong"


def test_non_browser_client_without_origin_is_allowed(client: TestClient) -> None:
    with client.websocket_connect("/ws/events") as ws:
        ws.send_text("ping")
        assert ws.receive_text() == "pong"


def test_foreign_origin_is_rejected(client: TestClient) -> None:
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect("/ws/events", headers={"origin": "https://evil.example"}) as ws:
            ws.receive_text()
    assert exc.value.code == 1008


def test_connection_limit(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(settings, "ws_max_connections", 0)
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect("/ws/events") as ws:
            ws.receive_text()
    assert exc.value.code == 1013
    assert connection_manager.connection_count == 0
