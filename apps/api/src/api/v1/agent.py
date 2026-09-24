"""Map agent endpoints (M4). Disabled (503) unless ANTHROPIC_API_KEY is set."""

import logging
from functools import lru_cache
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import get_settings
from src.db.database import get_db
from src.schemas.agent import AgentChatRequest, AgentChatResponse, AgentStatus
from src.services.agent.budget import AgentBudget, BudgetExceeded
from src.services.agent.service import AgentService, MessagesClient, StepLimitReached
from src.services.event_service import EventService

logger = logging.getLogger(__name__)
router = APIRouter()


@lru_cache
def _anthropic_client(api_key: str) -> MessagesClient:
    from anthropic import AsyncAnthropic

    return AsyncAnthropic(api_key=api_key)


def get_agent_client() -> MessagesClient | None:
    key = get_settings().anthropic_api_key
    return _anthropic_client(key.get_secret_value()) if key else None


def _budget(session: AsyncSession) -> AgentBudget:
    settings = get_settings()
    return AgentBudget(session, settings.agent_session_token_cap, settings.agent_daily_token_cap)


@router.get("/status", response_model=AgentStatus)
async def agent_status(
    client: Annotated[MessagesClient | None, Depends(get_agent_client)],
) -> AgentStatus:
    settings = get_settings()
    return AgentStatus(
        enabled=client is not None,
        model=settings.agent_model if client else None,
        session_cap=settings.agent_session_token_cap,
    )


@router.get("/usage")
async def agent_usage(
    session_id: Annotated[UUID, Query()],
    session: AsyncSession = Depends(get_db),
) -> dict[str, int]:
    budget = _budget(session)
    return {"session_tokens": await budget.session_tokens(session_id), "session_cap": budget.session_cap}


@router.post("/chat", response_model=AgentChatResponse)
async def agent_chat(
    request: AgentChatRequest,
    client: Annotated[MessagesClient | None, Depends(get_agent_client)],
    session: AsyncSession = Depends(get_db),
) -> AgentChatResponse:
    if client is None:
        raise HTTPException(status_code=503, detail="The map assistant is not configured")
    settings = get_settings()
    agent = AgentService(
        client=client,
        events=EventService(session),
        budget=_budget(session),
        model=settings.agent_model,
        max_output_tokens=settings.agent_max_output_tokens,
        max_steps=settings.agent_max_steps,
    )
    try:
        return await agent.chat(request)
    except BudgetExceeded as e:
        raise HTTPException(status_code=429, detail=f"agent_budget_{e.scope}") from e
    except StepLimitReached as e:
        raise HTTPException(status_code=502, detail="The assistant could not finish; try a simpler question") from e
    except Exception as e:
        # Upstream model errors: log details, show nothing internal
        logger.exception("agent chat failed")
        raise HTTPException(status_code=502, detail="The assistant is unavailable right now") from e
