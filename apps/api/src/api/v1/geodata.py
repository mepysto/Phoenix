from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.database import get_db
from src.schemas.event import ClusterResponse, EventFilter, GeoJSONFeatureCollection
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
    types: Annotated[list[str] | None, Query()] = None,
    severities: Annotated[list[str] | None, Query()] = None,
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
    types: Annotated[list[str] | None, Query()] = None,
    severities: Annotated[list[str] | None, Query()] = None,
    start_date: str | None = None,
    end_date: str | None = None,
    min_lng: float | None = None,
    min_lat: float | None = None,
    max_lng: float | None = None,
    max_lat: float | None = None,
    is_active: bool | None = None,
    include_properties: bool = True,
    limit: int = Query(default=1000, le=5000),
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
