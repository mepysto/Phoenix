"""Public data source status (feeds the source status panel)."""

from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.database import get_db
from src.models.event import DataSource
from src.repositories.data_source_repository import DataSourceRepository

router = APIRouter()

SourceHealth = Literal["fresh", "stale", "failing", "never"]

# A source is stale after missing this many scheduled syncs (min 15 minutes)
STALE_AFTER_INTERVALS = 3
MIN_STALE_AFTER = timedelta(minutes=15)


class SourceStatus(BaseModel):
    name: str
    type: str
    is_realtime: bool
    status: SourceHealth
    last_sync: datetime | None
    sync_interval_minutes: int | None
    consecutive_failures: int
    # Exception type only; internal error details stay in the server logs
    last_error: str | None


def source_health(source: DataSource, now: datetime) -> SourceHealth:
    """Classify a source for display. last_sync is the last *successful* sync."""
    if source.last_sync is None:
        return "never"
    if source.last_sync_status == "failed" and source.consecutive_failures > 0:
        return "failing"
    interval = timedelta(minutes=source.sync_interval_minutes or 5)
    if now - source.last_sync > max(interval * STALE_AFTER_INTERVALS, MIN_STALE_AFTER):
        return "stale"
    return "fresh"


@router.get("", response_model=list[SourceStatus])
async def list_source_status(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[SourceStatus]:
    """Freshness of every active data source, alphabetically."""
    now = datetime.now(UTC)
    sources = await DataSourceRepository(session).list_active()
    return [
        SourceStatus(
            name=s.name,
            type=s.type,
            is_realtime=s.is_realtime,
            status=(health := source_health(s, now)),
            last_sync=s.last_sync,
            sync_interval_minutes=s.sync_interval_minutes,
            consecutive_failures=s.consecutive_failures,
            last_error=s.last_sync_error if health == "failing" else None,
        )
        for s in sorted(sources, key=lambda s: s.name.lower())
    ]
