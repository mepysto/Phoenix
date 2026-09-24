"""Map agent loop against PostGIS with a scripted model (TEST_DATABASE_URL)."""

import json
import os
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from src.api.v1.agent import get_agent_client
from src.core.config import get_settings
from src.db.database import get_db
from src.main import app
from src.models.event import EventType, SeverityLevel
from src.repositories.event_repository import EventRepository

DB_URL = os.getenv("TEST_DATABASE_URL", "").replace("postgresql://", "postgresql+asyncpg://", 1)
pytestmark = pytest.mark.skipif(not DB_URL, reason="TEST_DATABASE_URL not set")

CHAT = "/api/v1/agent/chat"


def tool_use(name, **args):
    return SimpleNamespace(type="tool_use", id=f"toolu_{uuid4().hex[:8]}", name=name, input=args)


def say(text_):
    return SimpleNamespace(type="text", text=text_)


class ScriptedModel:
    """Plays back responses; each step may be a function of the conversation so far."""

    def __init__(self, steps, tokens=(100, 20)):
        self.steps = list(steps)
        self.tokens = tokens
        self.calls = []
        self.messages = self

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        step = self.steps.pop(0)
        content = step(kwargs["messages"]) if callable(step) else step
        return SimpleNamespace(
            content=content,
            stop_reason="tool_use" if any(b.type == "tool_use" for b in content) else "end_turn",
            usage=SimpleNamespace(input_tokens=self.tokens[0], output_tokens=self.tokens[1]),
        )


def last_tool_results(messages):
    return messages[-1]["content"]


@pytest.fixture
async def setup():
    engine = create_async_engine(DB_URL, poolclass=NullPool)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as s:
        await s.execute(text("TRUNCATE events, event_sources, data_sources, agent_usage CASCADE"))
        quake = await EventRepository(s).create(
            type=EventType.earthquake, title="M 6.2 - Near Tokyo", severity=SeverityLevel.high,
            lat=35.7, lng=139.7, start_date=datetime(2026, 9, 23, tzinfo=UTC), is_active=True,
        )
        await s.commit()

    async def override_db():
        async with maker() as session:
            yield session

    state = {"model": None}
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_agent_client] = lambda: state["model"]
    with TestClient(app) as client:
        yield client, state, str(quake.id)
    app.dependency_overrides.clear()
    await engine.dispose()


def body(message="Show me the Tokyo earthquake", **context):
    return {
        "session_id": str(uuid4()),
        "messages": [{"role": "user", "content": message}],
        "context": {"available_layers": ["shakemaps", "fires"], **context},
    }


def test_searches_then_acts_on_the_map(setup):
    client, state, quake_id = setup

    def act_on_result(messages):
        found = json.loads(last_tool_results(messages)[0]["content"])
        event = found["events"][0]
        return [
            tool_use("select_event", event_id=event["id"]),
            tool_use("set_layers", show=["shakemaps"]),
        ]

    state["model"] = model = ScriptedModel([
        [say("Let me look."), tool_use("search_events", query="Tokyo", types=["earthquake"])],
        act_on_result,
        [say("Here is the M 6.2 earthquake near Tokyo, with its ShakeMap.")],
    ])
    response = client.post(CHAT, json=body(bbox=[130, 30, 145, 40]))
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["reply"] == "Here is the M 6.2 earthquake near Tokyo, with its ShakeMap."
    assert data["actions"] == [
        {"type": "select_event", "event_id": quake_id},
        {"type": "set_layers", "show": ["shakemaps"], "hide": []},
    ]
    assert [c["name"] for c in data["tool_calls"]] == ["search_events", "select_event", "set_layers"]
    assert all(c["ok"] for c in data["tool_calls"])
    assert data["usage"] == {"session_tokens": 360, "session_cap": get_settings().agent_session_token_cap}
    # Grounding: the view is in the system prompt
    assert '"bbox":[130.0,30.0,145.0,40.0]' in model.calls[0]["system"]


def test_invalid_map_action_is_reported_to_the_model_not_forwarded(setup):
    client, state, _ = setup

    def check_error(messages):
        result = last_tool_results(messages)[0]
        assert result["is_error"] is True
        assert "unknown layer ids ['nuclear-sites']" in result["content"]
        return [say("That layer is not available.")]

    state["model"] = ScriptedModel([[tool_use("set_layers", show=["nuclear-sites"])], check_error])
    data = client.post(CHAT, json=body("Show nuclear sites")).json()
    assert data["actions"] == []
    assert data["tool_calls"] == [{"name": "set_layers", "ok": False}]


def test_session_cap_stops_further_calls(setup, monkeypatch):
    client, state, _ = setup
    monkeypatch.setattr(get_settings(), "agent_session_token_cap", 150)
    request = body("hello")
    state["model"] = ScriptedModel([[say("Hi")], [say("Hi again")]])
    assert client.post(CHAT, json=request).status_code == 200  # uses 120
    assert client.post(CHAT, json=request).status_code == 200  # 120 < 150: allowed, now 240
    third = client.post(CHAT, json=request)
    assert third.status_code == 429
    assert third.json()["detail"] == "agent_budget_session"


def test_daily_cap_applies_across_sessions(setup, monkeypatch):
    client, state, _ = setup
    monkeypatch.setattr(get_settings(), "agent_daily_token_cap", 100)
    state["model"] = ScriptedModel([[say("Hi")]])
    assert client.post(CHAT, json=body("hello")).status_code == 200
    other_session = client.post(CHAT, json=body("hello"))
    assert other_session.status_code == 429
    assert other_session.json()["detail"] == "agent_budget_daily"


def test_disabled_without_key(setup):
    client, state, _ = setup
    state["model"] = None
    assert client.get("/api/v1/agent/status").json()["enabled"] is False
    assert client.post(CHAT, json=body()).status_code == 503


def test_step_limit(setup, monkeypatch):
    client, state, _ = setup
    monkeypatch.setattr(get_settings(), "agent_max_steps", 2)
    state["model"] = ScriptedModel([[tool_use("view_summary")], [tool_use("view_summary")]])
    assert client.post(CHAT, json=body()).status_code == 502


def test_request_validation(setup):
    client, state, _ = setup
    state["model"] = ScriptedModel([])
    ends_with_assistant = body()
    ends_with_assistant["messages"].append({"role": "assistant", "content": "ok"})
    assert client.post(CHAT, json=ends_with_assistant).status_code == 422
    assert client.post(CHAT, json=body("x" * 4001)).status_code == 422
    assert client.post(CHAT, json=body(bbox=[0, 50, 10, 40])).status_code == 422
