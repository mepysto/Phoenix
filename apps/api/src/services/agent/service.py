"""Map agent: a tool-calling loop grounded in what the user is looking at (M4)."""

import json
import logging
from datetime import UTC, datetime
from typing import Any, Protocol

from src.schemas.agent import (
    AgentChatRequest,
    AgentChatResponse,
    AgentUsageInfo,
    MapAction,
    MapContext,
    ToolCallRecord,
)
from src.services.agent.budget import AgentBudget
from src.services.agent.tools import (
    MAP_TOOL_NAMES,
    TOOLS,
    ToolError,
    run_data_tool,
    validate_map_action,
)
from src.services.event_service import EventService

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are the Phoenix map assistant. Phoenix is a public map of \
natural disasters and humanitarian crises (sources: GDACS, USGS, NASA EONET, \
Copernicus EMS, NASA FIRMS and others) used for disaster response and recovery.

Rules:
- Facts about events come only from your tools. Never invent events, numbers, \
dates or places; if the tools return nothing, say so.
- Only say you changed the map if the map tool call succeeded.
- Prefer showing over telling: move the map, filter it or open an event when \
that answers the question, then explain briefly.
- Phoenix does not track or identify individual people. Refuse requests to \
locate, follow or identify a specific person.
- Answer in the language of the user's last message, concisely.

Current time (UTC): {now}
The user's map right now (JSON): {context}"""


class MessagesClient(Protocol):
    """The part of anthropic.AsyncAnthropic the agent uses (swappable in tests)."""

    @property
    def messages(self) -> Any: ...


class StepLimitReached(Exception):
    pass


def _context_json(context: MapContext) -> str:
    return context.model_dump_json(exclude_none=True)


class AgentService:
    def __init__(
        self,
        client: MessagesClient,
        events: EventService,
        budget: AgentBudget,
        model: str,
        max_output_tokens: int,
        max_steps: int,
    ) -> None:
        self.client = client
        self.events = events
        self.budget = budget
        self.model = model
        self.max_output_tokens = max_output_tokens
        self.max_steps = max_steps

    async def chat(self, request: AgentChatRequest) -> AgentChatResponse:
        system = SYSTEM_PROMPT.format(
            now=datetime.now(UTC).isoformat(timespec="minutes"),
            context=_context_json(request.context),
        )
        messages: list[dict[str, Any]] = [m.model_dump() for m in request.messages]
        actions: list[MapAction] = []
        calls: list[ToolCallRecord] = []
        reply_parts: list[str] = []

        for _ in range(self.max_steps):
            await self.budget.check(request.session_id)
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=self.max_output_tokens,
                system=system,
                messages=messages,
                tools=TOOLS,
            )
            await self.budget.record(
                request.session_id, response.usage.input_tokens, response.usage.output_tokens
            )
            reply_parts = [b.text for b in response.content if b.type == "text"]
            if response.stop_reason != "tool_use":
                break
            results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue
                content, ok = await self._run_tool(block.name, block.input, request.context, actions)
                calls.append(ToolCallRecord(name=block.name, ok=ok))
                results.append(
                    {"type": "tool_result", "tool_use_id": block.id, "content": content, "is_error": not ok}
                )
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": results})
        else:
            raise StepLimitReached

        return AgentChatResponse(
            reply="\n\n".join(p.strip() for p in reply_parts if p.strip()),
            actions=actions,
            tool_calls=calls,
            usage=AgentUsageInfo(
                session_tokens=await self.budget.session_tokens(request.session_id),
                session_cap=self.budget.session_cap,
            ),
        )

    async def _run_tool(
        self, name: str, args: Any, context: MapContext, actions: list[MapAction]
    ) -> tuple[str, bool]:
        if not isinstance(args, dict):
            return "tool input must be an object", False
        try:
            if name in MAP_TOOL_NAMES:
                actions.append(validate_map_action(name, args, context))
                return "done: applied to the user's map", True
            result = await run_data_tool(name, args, self.events, context)
            return json.dumps(result, ensure_ascii=False, default=str), True
        except ToolError as e:
            return str(e), False
        except Exception:
            logger.exception("agent tool %s failed", name)
            return "the tool failed; try something else", False
