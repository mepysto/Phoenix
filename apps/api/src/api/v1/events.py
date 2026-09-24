"""Events API endpoints for disaster event management."""

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.database import get_db
from src.models.event import EventType, SeverityLevel
from src.schemas.event import (
    EventDetailResponse,
    EventFilter,
    EventListResponse,
    TimelineBucket,
    TimelineResponse,
)
from src.repositories.event_repository import EventRepository
from src.services.event_service import EventService

router = APIRouter()


def get_event_service(session: AsyncSession = Depends(get_db)) -> EventService:
    """Dependency to create EventService with database session.

    Args:
        session: AsyncSession injected from get_db dependency

    Returns:
        EventService instance with database connection
    """
    return EventService(session)


@router.get("", response_model=EventListResponse)
async def list_events(
    event_service: Annotated[EventService, Depends(get_event_service)],
    q: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    types: Annotated[list[EventType] | None, Query()] = None,
    severities: Annotated[list[SeverityLevel] | None, Query()] = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    min_lng: float | None = None,
    min_lat: float | None = None,
    max_lng: float | None = None,
    max_lat: float | None = None,
    center_lat: float | None = Query(default=None, ge=-90, le=90),
    center_lng: float | None = Query(default=None, ge=-180, le=180),
    radius_km: float | None = Query(default=None, gt=0, le=500),
    is_active: bool | None = None,
    at: datetime | None = Query(default=None, description="Only events ongoing at this time"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> EventListResponse:
    """List disaster events with filtering and pagination.

    Args:
        event_service: Injected EventService instance
        types: Filter by event types (earthquake, flood, etc.)
        severities: Filter by severity levels (low, medium, high, critical)
        start_date: Filter events starting from this date
        end_date: Filter events up to this date
        min_lng: Bounding box minimum longitude
        min_lat: Bounding box minimum latitude
        max_lng: Bounding box maximum longitude
        max_lat: Bounding box maximum latitude
        center_lat: Center latitude for radius search (-90 to 90)
        center_lng: Center longitude for radius search (-180 to 180)
        radius_km: Search radius in km (max 500km)
        is_active: Filter by active status
        limit: Maximum number of events to return (default 50, max 200)
        offset: Number of events to skip for pagination

    Returns:
        EventListResponse with paginated event data
    """
    filters = EventFilter(
        q=q,
        types=types,
        severities=severities,
        start_date=start_date,
        end_date=end_date,
        min_lng=min_lng,
        min_lat=min_lat,
        max_lng=max_lng,
        max_lat=max_lat,
        center_lat=center_lat,
        center_lng=center_lng,
        radius_km=radius_km,
        is_active=is_active,
        at=at,
    )
    return await event_service.list_events(filters, limit, offset)


TIMELINE_MAX_BUCKETS = {"hour": 24 * 14, "day": 366, "week": 520}


@router.get("/timeline", response_model=TimelineResponse)
async def event_timeline(
    session: Annotated[AsyncSession, Depends(get_db)],
    start: datetime,
    end: datetime,
    bucket: Literal["hour", "day", "week"] = "day",
    types: Annotated[list[EventType] | None, Query()] = None,
    severities: Annotated[list[SeverityLevel] | None, Query()] = None,
) -> TimelineResponse:
    """Event onsets per time bucket (by type) for the timeline histogram.

    Declared before /{event_id} so "timeline" is not parsed as a UUID.
    """
    if end <= start:
        raise HTTPException(status_code=422, detail="end must be after start")
    span = {"hour": 3600, "day": 86400, "week": 604800}[bucket]
    if (end - start).total_seconds() / span > TIMELINE_MAX_BUCKETS[bucket]:
        raise HTTPException(status_code=422, detail="Range too long for this bucket size")
    rows = await EventRepository(session).timeline(
        EventFilter(types=types, severities=severities), start, end, bucket
    )
    grouped: dict[datetime, dict[str, int]] = {}
    for bucket_start, event_type, count in rows:
        grouped.setdefault(bucket_start, {})[event_type] = count
    return TimelineResponse(
        bucket=bucket,
        start=start,
        end=end,
        buckets=[
            TimelineBucket(start=t, total=sum(by_type.values()), by_type=by_type)
            for t, by_type in grouped.items()
        ],
    )


@router.get("/{event_id}", response_model=EventDetailResponse)
async def get_event(
    event_id: UUID,
    event_service: Annotated[EventService, Depends(get_event_service)],
) -> EventDetailResponse:
    """Get detailed information for a specific event.

    Args:
        event_id: UUID of the event to retrieve
        event_service: Injected EventService instance

    Returns:
        EventDetailResponse with full event details

    Raises:
        HTTPException: 404 if event not found
    """
    event = await event_service.get_event(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@router.get("/{event_id}/layers")
async def get_event_layers(
    event_id: UUID,
    event_service: Annotated[EventService, Depends(get_event_service)],
) -> dict:
    """Get geographic layers for a specific event.

    Args:
        event_id: UUID of the event
        event_service: Injected EventService instance

    Returns:
        Dictionary with layers list (currently empty in Phase 2)
    """
    layers = await event_service.get_event_layers(event_id)
    return {"layers": layers}
