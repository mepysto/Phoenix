"""Hard token caps for the map agent, stored in PostgreSQL so every worker shares them.

Checked before each model call. Concurrent requests can overshoot a cap by
at most one call each (max_output_tokens plus the prompt), which is bounded.
"""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.agent_usage import AgentUsage


class BudgetExceeded(Exception):
    def __init__(self, scope: str) -> None:
        super().__init__(f"agent {scope} token budget exhausted")
        self.scope = scope  # "session" | "daily"


def _today():
    return datetime.now(UTC).date()


class AgentBudget:
    def __init__(self, session: AsyncSession, session_cap: int, daily_cap: int) -> None:
        self.session = session
        self.session_cap = session_cap
        self.daily_cap = daily_cap

    async def session_tokens(self, session_id: UUID) -> int:
        total = await self.session.scalar(
            select(func.coalesce(func.sum(AgentUsage.input_tokens + AgentUsage.output_tokens), 0))
            .where(AgentUsage.session_id == session_id)
        )
        return int(total or 0)

    async def check(self, session_id: UUID) -> None:
        daily = await self.session.scalar(
            select(func.coalesce(func.sum(AgentUsage.input_tokens + AgentUsage.output_tokens), 0))
            .where(AgentUsage.day == _today())
        )
        if int(daily or 0) >= self.daily_cap:
            raise BudgetExceeded("daily")
        if await self.session_tokens(session_id) >= self.session_cap:
            raise BudgetExceeded("session")

    async def record(self, session_id: UUID, input_tokens: int, output_tokens: int) -> None:
        stmt = insert(AgentUsage).values(
            day=_today(),
            session_id=session_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            requests=1,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=[AgentUsage.day, AgentUsage.session_id],
            set_={
                "input_tokens": AgentUsage.input_tokens + stmt.excluded.input_tokens,
                "output_tokens": AgentUsage.output_tokens + stmt.excluded.output_tokens,
                "requests": AgentUsage.requests + 1,
            },
        )
        await self.session.execute(stmt)
        # Committed right away: spend must count even if the request fails later
        await self.session.commit()
