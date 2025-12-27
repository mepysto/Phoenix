from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from src.schemas.event import EventFilter, EventListResponse, EventResponse, EventDetailResponse
from src.services.event_service import EventService

router = APIRouter()


def get_event_service() -> EventService:
    return EventService()


@router.get("", response_model=EventListResponse)
async def list_events(
    event_service: Annotated[EventService, Depends(get_event_service)],
    types: Annotated[list[str] | None, Query()] = None,
    severities: Annotated[list[str] | None, Query()] = None,
    start_date: str | None = None,
    end_date: str | None = None,
    min_lng: float | None = None,
    min_lat: float | None = None,
    max_lng: float | None = None,
    max_lat: float | None = None,
    is_active: bool | None = None,
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
) -> EventListResponse:
    filters = EventFilter(
        types=types,
        severities=severities,
        start_date=start_date,
        end_date=end_date,
        min_lng=min_lng,
        min_lat=min_lat,
        max_lng=max_lng,
        max_lat=max_lat,
        is_active=is_active,
    )
    return await event_service.list_events(filters, limit, offset)


@router.get("/{event_id}", response_model=EventDetailResponse)
async def get_event(
    event_id: UUID,
    event_service: Annotated[EventService, Depends(get_event_service)],
) -> EventDetailResponse:
    event = await event_service.get_event(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@router.get("/{event_id}/layers")
async def get_event_layers(
    event_id: UUID,
    event_service: Annotated[EventService, Depends(get_event_service)],
) -> dict:
    layers = await event_service.get_event_layers(event_id)
    return {"layers": layers}
