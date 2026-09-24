"""The agent loop through the real Anthropic SDK, with HTTP mocked.

Checks what goes over the wire (tools, system prompt, tool results) and that
real SDK response objects drive the loop, without an API key or network.
"""

import json
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import httpx2
import pytest
from anthropic import AsyncAnthropic

from src.schemas.agent import AgentChatRequest
from src.services.agent.service import AgentService
from src.services.agent.tools import TOOLS


def _message(content, stop_reason):
    return {
        "id": f"msg_{uuid4().hex[:8]}",
        "type": "message",
        "role": "assistant",
        "model": "claude-sonnet-5",
        "content": content,
        "stop_reason": stop_reason,
        "stop_sequence": None,
        "usage": {"input_tokens": 50, "output_tokens": 10},
    }


@pytest.mark.asyncio
async def test_loop_over_the_real_sdk():
    sent = []
    replies = [
        _message(
            [{"type": "tool_use", "id": "toolu_1", "name": "fly_to", "input": {"lat": 35.7, "lng": 139.7, "zoom": 6}}],
            "tool_use",
        ),
        _message([{"type": "text", "text": "Moved the map to Tokyo."}], "end_turn"),
    ]

    def handler(request: httpx2.Request) -> httpx2.Response:
        sent.append(json.loads(request.content))
        return httpx2.Response(200, json=replies[len(sent) - 1])

    client = AsyncAnthropic(api_key="test-key", http_client=httpx2.AsyncClient(transport=httpx2.MockTransport(handler)))
    budget = MagicMock(session_cap=1000, check=AsyncMock(), record=AsyncMock(), session_tokens=AsyncMock(return_value=120))
    agent = AgentService(client, events=MagicMock(), budget=budget, model="claude-sonnet-5", max_output_tokens=512, max_steps=4)

    result = await agent.chat(
        AgentChatRequest.model_validate(
            {"session_id": str(uuid4()), "messages": [{"role": "user", "content": "Go to Tokyo"}]}
        )
    )

    assert result.reply == "Moved the map to Tokyo."
    assert [a.model_dump() for a in result.actions] == [{"type": "fly_to", "lat": 35.7, "lng": 139.7, "zoom": 6.0}]
    first, second = sent
    assert first["model"] == "claude-sonnet-5" and first["max_tokens"] == 512
    assert [t["name"] for t in first["tools"]] == [t["name"] for t in TOOLS]
    assert "Phoenix map assistant" in first["system"]
    # The assistant turn is replayed as SDK blocks, followed by our tool result
    assert second["messages"][1]["role"] == "assistant"
    assert second["messages"][1]["content"][0]["type"] == "tool_use"
    assert second["messages"][2]["content"] == [
        {"type": "tool_result", "tool_use_id": "toolu_1", "content": "done: applied to the user's map", "is_error": False}
    ]
    budget.record.assert_awaited_with(budget.record.await_args.args[0], 50, 10)
    assert budget.record.await_count == 2


def test_tool_schemas_are_valid_json_schema_objects():
    for tool in TOOLS:
        schema = tool["input_schema"]
        assert schema["type"] == "object", tool["name"]
        assert set(schema.get("required", [])) <= set(schema["properties"]), tool["name"]
