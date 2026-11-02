"""Public overview figures for the dashboard."""

from typing import Annotated

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.database import get_db
from src.services.stats_service import OverviewStats, StatsService

router = APIRouter()


@router.get("/overview", response_model=OverviewStats)
async def overview(
    response: Response, session: Annotated[AsyncSession, Depends(get_db)]
) -> OverviewStats:
    """Active events, people affected, onsets per week and community activity.

    Aggregates public data only. Cached briefly: the figures move with the
    5-minute feed sync, not per request.
    """
    response.headers["Cache-Control"] = "public, max-age=60"
    return await StatsService(session).overview()
