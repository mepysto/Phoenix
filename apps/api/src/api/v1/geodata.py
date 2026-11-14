from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.database import get_db
from src.models.event import EventType, SeverityLevel
from src.schemas.event import (
    ClusterResponse,
    EventFilter,
    GeoJSONFeatureCollection,
    NearbyResponse,
    ViewSummary,
)
from src.services.clustering_service import ClusteringService
from src.services.event_service import EventService

router = APIRouter()


def get_event_service(session: AsyncSession = Depends(get_db)) -> EventService:
    return EventService(session)


def get_clustering_service(session: AsyncSession = Depends(get_db)) -> ClusteringService:
    return ClusteringService(session)


@router.get("/tiles/{z}/{x}/{y}")
async def get_vector_tile(z: int, x: int, y: int) -> Response:
    return Response(content=b"", media_type="application/x-protobuf")


@router.get("/events/clusters", response_model=ClusterResponse)
async def get_event_clusters(
    clustering_service: Annotated[ClusteringService, Depends(get_clustering_service)],
    zoom: int = Query(..., ge=0, le=20, description="Map zoom level (0-20)"),
    min_lat: float | None = None,
    max_lat: float | None = None,
    min_lng: float | None = None,
    max_lng: float | None = None,
    types: Annotated[list[EventType] | None, Query()] = None,
    severities: Annotated[list[SeverityLevel] | None, Query()] = None,
    is_active: bool | None = True,
) -> ClusterResponse:
    filters = EventFilter(
        types=types,
        severities=severities,
        min_lat=min_lat,
        max_lat=max_lat,
        min_lng=min_lng,
        max_lng=max_lng,
        is_active=is_active,
    )
    return await clustering_service.get_clusters(zoom=zoom, filters=filters)


@router.get("/events/geojson", response_model=GeoJSONFeatureCollection)
async def get_events_geojson(
    event_service: Annotated[EventService, Depends(get_event_service)],
    types: Annotated[list[EventType] | None, Query()] = None,
    severities: Annotated[list[SeverityLevel] | None, Query()] = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    min_lng: float | None = None,
    min_lat: float | None = None,
    max_lng: float | None = None,
    max_lat: float | None = None,
    is_active: bool | None = None,
    include_properties: bool = True,
    limit: int = Query(default=1000, ge=1, le=5000),
) -> GeoJSONFeatureCollection:
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
    return await event_service.get_events_as_geojson(
        filters=filters,
        include_properties=include_properties,
        limit=limit,
    )


def _view_filter(
    types: list[EventType] | None,
    severities: list[SeverityLevel] | None,
    at: datetime | None,
    q: str | None = None,
    start_date: datetime | None = None,
    **bbox: float | None,
) -> EventFilter:
    # A past instant has its own "ongoing" test; otherwise only active events.
    # Search and period match the event list, so the map's figures agree with it.
    return EventFilter(
        types=types, severities=severities, at=at, q=q, start_date=start_date,
        is_active=None if at else True, **bbox,
    )


@router.get("/summary", response_model=ViewSummary)
async def get_view_summary(
    event_service: Annotated[EventService, Depends(get_event_service)],
    min_lng: float | None = Query(default=None, ge=-180, le=180),
    min_lat: float | None = Query(default=None, ge=-90, le=90),
    max_lng: float | None = Query(default=None, ge=-180, le=180),
    max_lat: float | None = Query(default=None, ge=-90, le=90),
    types: Annotated[list[EventType] | None, Query()] = None,
    severities: Annotated[list[SeverityLevel] | None, Query()] = None,
    at: datetime | None = Query(default=None, description="Events ongoing at this time"),
    q: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    start_date: datetime | None = Query(default=None, description="Events that began at or after this time"),
) -> ViewSummary:
    """Totals for the current map view (omit the bbox for the whole world)."""
    filters = _view_filter(
        types, severities, at, q, start_date,
        min_lng=min_lng, min_lat=min_lat, max_lng=max_lng, max_lat=max_lat,
    )
    return await event_service.summarize_view(filters)


@router.get("/nearby", response_model=NearbyResponse)
async def get_nearby_events(
    event_service: Annotated[EventService, Depends(get_event_service)],
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
    radius_km: float = Query(default=1000, gt=0, le=5000),
    limit: int = Query(default=20, ge=1, le=50),
    types: Annotated[list[EventType] | None, Query()] = None,
    severities: Annotated[list[SeverityLevel] | None, Query()] = None,
    at: datetime | None = Query(default=None, description="Events ongoing at this time"),
    q: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    start_date: datetime | None = Query(default=None, description="Events that began at or after this time"),
) -> NearbyResponse:
    """Events around a point, nearest first."""
    filters = _view_filter(types, severities, at, q, start_date)
    return await event_service.nearby(filters, lat, lng, radius_km, limit)
