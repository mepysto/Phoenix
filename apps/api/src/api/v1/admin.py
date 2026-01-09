"""Admin API endpoints for system management."""

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.database import async_session_maker, get_db
from src.models.event import DataSource, Event, EventSource, EventType
from src.services.broadcaster import connection_manager
from src.services.dedup.offline_merge_service import (
    OfflineMergeConfig,
    OfflineMergeService,
    OfflineMergeStats,
)
from src.services.scheduler import scheduler_service

logger = logging.getLogger(__name__)
router = APIRouter()


class MergeJobResponse(BaseModel):
    status: str
    message: str
    job_id: str | None = None


class MergeStatsResponse(BaseModel):
    scanned: int
    groups_found: int
    merges_applied: int
    sources_relinked: int
    duplicates_marked: int
    skipped: int
    errors: list[str]


@router.get("/status")
async def admin_status() -> dict[str, Any]:
    """Get overall system status."""
    scheduler_status = scheduler_service.get_status()

    return {
        "websocket": {
            "active_connections": connection_manager.connection_count,
        },
        "scheduler": scheduler_status,
    }


@router.get("/dedup/status")
async def dedup_status(
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get deduplication statistics."""
    # Count events
    event_count = await session.execute(select(func.count(Event.id)))
    total_events = event_count.scalar_one()

    # Count event sources
    source_count = await session.execute(select(func.count(EventSource.id)))
    total_sources = source_count.scalar_one()

    # Events with multiple sources (successfully deduplicated)
    multi_source_query = (
        select(Event.id)
        .join(EventSource)
        .group_by(Event.id)
        .having(func.count(EventSource.id) > 1)
    )
    multi_source_result = await session.execute(
        select(func.count()).select_from(multi_source_query.subquery())
    )
    multi_source_events = multi_source_result.scalar_one()

    # Events by source
    sources_query = (
        select(DataSource.name, func.count(EventSource.id))
        .join(EventSource, DataSource.id == EventSource.source_id)
        .group_by(DataSource.name)
    )
    sources_result = await session.execute(sources_query)
    events_by_source = {name: count for name, count in sources_result.all()}

    return {
        "total_events": total_events,
        "total_event_sources": total_sources,
        "multi_source_events": multi_source_events,
        "dedup_ratio": round(multi_source_events / total_events, 3) if total_events > 0 else 0,
        "events_by_source": events_by_source,
    }


@router.post("/sync/trigger")
async def trigger_sync(
    background_tasks: BackgroundTasks,
    source: str | None = None,
) -> dict[str, str]:
    """Manually trigger data synchronization.

    Args:
        source: Optional source name (gdacs, usgs, eonet, copernicus).
                If not provided, syncs all sources.
    """
    valid_sources = ["gdacs", "usgs", "eonet", "copernicus"]

    if source and source.lower() not in valid_sources:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid source. Must be one of: {valid_sources}",
        )

    if source:
        source = source.lower()
        if source == "gdacs":
            background_tasks.add_task(scheduler_service.sync_gdacs)
        elif source == "usgs":
            background_tasks.add_task(scheduler_service.sync_usgs)
        elif source == "eonet":
            background_tasks.add_task(scheduler_service.sync_eonet)
        elif source == "copernicus":
            background_tasks.add_task(scheduler_service.sync_copernicus)
        return {"status": "triggered", "source": source}
    else:
        # Sync all
        background_tasks.add_task(scheduler_service.sync_gdacs)
        background_tasks.add_task(scheduler_service.sync_usgs)
        background_tasks.add_task(scheduler_service.sync_eonet)
        background_tasks.add_task(scheduler_service.sync_copernicus)
        return {"status": "triggered", "source": "all"}


async def _run_offline_merge_background(
    config: OfflineMergeConfig,
    scope: str,
    since: datetime | None,
    event_types: list[EventType] | None,
) -> None:
    try:
        async with async_session_maker() as session:
            service = OfflineMergeService(session, config)
            stats = await service.run(
                scope=scope,  # type: ignore[arg-type]
                since=since,
                event_types=event_types,
            )
            logger.info(
                f"Offline merge completed: groups_found={stats.groups_found}, "
                f"merges_applied={stats.merges_applied}, "
                f"duplicates_marked={stats.duplicates_marked}, "
                f"errors={len(stats.errors)}"
            )
            if stats.errors:
                for error in stats.errors[:5]:
                    logger.warning(f"Merge error: {error}")
    except Exception as e:
        logger.exception(f"Offline merge job failed: {e}")


@router.post("/merge/trigger", response_model=MergeJobResponse)
async def trigger_offline_merge(
    background_tasks: BackgroundTasks,
    dry_run: bool = Query(default=True, description="Preview without making changes"),
    scope: str = Query(default="all", description="Scope: all, active, or inactive"),
    since: str | None = Query(default=None, description="Process events since date (ISO format)"),
    types: str | None = Query(default=None, description="Comma-separated event types"),
) -> MergeJobResponse:
    """Trigger offline merge job to deduplicate existing events.

    This runs the merge job in the background. Use dry_run=true (default)
    to preview changes before applying them.
    """
    if scope not in ("all", "active", "inactive"):
        raise HTTPException(
            status_code=400,
            detail="Invalid scope. Must be one of: all, active, inactive",
        )

    since_dt = None
    if since:
        try:
            since_dt = datetime.fromisoformat(since)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid date format. Use ISO format (YYYY-MM-DD)",
            )

    event_types = None
    if types:
        event_types = []
        for t in types.split(","):
            t = t.strip().lower()
            try:
                event_types.append(EventType(t))
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unknown event type: {t}",
                )

    config = OfflineMergeConfig(dry_run=dry_run)

    logger.info(
        f"Triggering offline merge: dry_run={dry_run}, scope={scope}, "
        f"since={since_dt}, types={event_types}"
    )

    background_tasks.add_task(
        _run_offline_merge_background, config, scope, since_dt, event_types
    )

    mode = "dry-run (preview)" if dry_run else "live (will modify data)"
    return MergeJobResponse(
        status="triggered",
        message=f"Offline merge job started in {mode} mode",
    )


@router.get("/merge/status")
async def get_merge_status(
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get merge statistics and status."""
    canonical_count = await session.execute(
        select(func.count(Event.id)).where(Event.is_canonical.is_(True))
    )
    total_canonical = canonical_count.scalar_one()

    merged_count = await session.execute(
        select(func.count(Event.id)).where(Event.merged_into_id.isnot(None))
    )
    total_merged = merged_count.scalar_one()

    total_count = await session.execute(select(func.count(Event.id)))
    total_events = total_count.scalar_one()

    glide_duplicates = await session.execute(
        select(func.count())
        .select_from(
            select(Event.glide_number)
            .where(Event.glide_number.isnot(None))
            .where(Event.is_canonical.is_(True))
            .group_by(Event.glide_number)
            .having(func.count(Event.id) > 1)
            .subquery()
        )
    )
    pending_glide_groups = glide_duplicates.scalar_one()

    return {
        "total_events": total_events,
        "canonical_events": total_canonical,
        "merged_events": total_merged,
        "pending_glide_duplicate_groups": pending_glide_groups,
    }
