from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.event import Event
from src.repositories.event_repository import EventRepository
from src.repositories.event_view_repository import EventViewRepository
from src.schemas.event import (
    DataSourceRef,
    DisplayPoint,
    EventDetailResponse,
    EventFilter,
    EventListResponse,
    EventResponse,
    GeoJSONFeature,
    GeoJSONFeatureCollection,
    GeoLayerResponse,
    Location,
    NearbyEvent,
    NearbyResponse,
    Pagination,
    ViewSummary,
)


class EventService:
    """Service for event operations using database repositories."""

    def __init__(self, session: AsyncSession):
        """Initialize EventService with database session.

        Args:
            session: AsyncSession for database operations
        """
        self.session = session
        self.event_repo = EventRepository(session)

    async def list_events(
        self, filters: EventFilter, limit: int, offset: int
    ) -> EventListResponse:
        """List events from DB with filtering and pagination.

        Args:
            filters: EventFilter with optional type, severity, date, bbox filters
            limit: Maximum number of events to return
            offset: Number of events to skip

        Returns:
            EventListResponse with paginated event data
        """
        # Use with_sources=True to eagerly load sources and avoid N+1
        events, total = await self.event_repo.list_events(
            filters, limit, offset, with_sources=True
        )

        data = [self._to_response(event) for event in events]

        return EventListResponse(
            data=data,
            pagination=Pagination(
                total=total,
                limit=limit,
                offset=offset,
                has_more=offset + limit < total,
            ),
        )

    async def get_event(self, event_id: UUID) -> EventDetailResponse | None:
        """Get event detail from DB including sources.

        Args:
            event_id: UUID of the event to retrieve

        Returns:
            EventDetailResponse if found, None otherwise
        """
        # Use method with eager loading for sources
        event = await self.event_repo.get_by_id_with_sources(event_id)
        if not event:
            return None

        return EventDetailResponse(
            **self._to_response(event).model_dump(),
            layers=[],  # Phase 2: empty list
            datasets=[],  # Phase 2: empty list
            metrics=[],  # Phase 2: empty list
        )

    async def get_event_layers(self, event_id: UUID) -> list[GeoLayerResponse]:
        return []

    async def get_events_as_geojson(
        self,
        filters: EventFilter,
        include_properties: bool = True,
        limit: int = 1000,
    ) -> GeoJSONFeatureCollection:
        events, total = await self.event_repo.list_events(
            filters, limit=limit, offset=0, with_sources=True
        )

        features: list[GeoJSONFeature] = []
        for event in events:
            geometry: dict[str, Any] | None = None
            if event.latitude is not None and event.longitude is not None:
                geometry = {
                    "type": "Point",
                    "coordinates": [event.longitude, event.latitude],
                }

            properties: dict[str, Any] = {}
            if include_properties:
                properties = {
                    "id": str(event.id),
                    "title": event.title,
                    "type": event.type.value,
                    "severity": event.severity.value,
                    "start_date": event.start_date.isoformat() if event.start_date else None,
                    "end_date": event.end_date.isoformat() if event.end_date else None,
                    "is_active": event.is_active,
                    "geo_precision": event.geo_precision.value if event.geo_precision else None,
                    "country_code": event.country_code,
                    "region": event.region,
                    "affected_population": event.affected_population,
                    "description": event.description,
                }

            features.append(GeoJSONFeature(
                geometry=geometry,
                properties=properties,
            ))

        return GeoJSONFeatureCollection(
            features=features,
            metadata={
                "total": total,
                "returned": len(features),
                "generated_at": datetime.now(timezone.utc).isoformat(),
            },
        )

    async def summarize_view(self, filters: EventFilter) -> ViewSummary:
        """Totals for the events matching a map view."""
        counts, population, last_updated = await EventViewRepository(self.session).summarize(filters)
        by_severity: dict[str, int] = {}
        by_type: dict[str, int] = {}
        for (event_type, severity), n in counts.items():
            by_severity[severity] = by_severity.get(severity, 0) + n
            by_type[event_type] = by_type.get(event_type, 0) + n
        return ViewSummary(
            total=sum(counts.values()),
            by_severity=by_severity,
            by_type=by_type,
            affected_population=population,
            last_updated=last_updated,
        )

    async def nearby(
        self, filters: EventFilter, lat: float, lng: float, radius_km: float, limit: int
    ) -> NearbyResponse:
        """Events around a point, nearest first."""
        rows = await EventViewRepository(self.session).nearest(filters, lat, lng, radius_km, limit)
        return NearbyResponse(
            center_lat=lat,
            center_lng=lng,
            radius_km=radius_km,
            data=[
                NearbyEvent(event=self._to_response(event), distance_km=round(meters / 1000, 1))
                for event, meters in rows
            ],
        )

    def _to_response(self, event: Event) -> EventResponse:
        """Convert Event model to EventResponse schema.

        Args:
            event: Event SQLAlchemy model

        Returns:
            EventResponse Pydantic schema
        """
        location = Location(
            lat=event.latitude,
            lng=event.longitude,
            country=event.region,
            country_code=event.country_code,
        )

        display_point = self._compute_display_point(event)

        sources: list[DataSourceRef] = []
        try:
            for es in event.sources:
                if es.source:
                    sources.append(
                        DataSourceRef(
                            id=es.source.id,
                            name=es.source.name,
                            type=es.source.type,
                        )
                    )
        except Exception:
            pass

        return EventResponse(
            id=event.id,
            type=event.type.value,
            title=event.title,
            description=event.description,
            location=location,
            geo_precision=event.geo_precision.value if event.geo_precision else None,
            display_point=display_point,
            severity=event.severity.value,
            affected_population=event.affected_population,
            start_date=event.start_date,
            end_date=event.end_date,
            is_active=event.is_active,
            sources=sources,
            created_at=event.created_at,
            updated_at=event.updated_at,
        )

    def _compute_display_point(self, event: Event) -> DisplayPoint | None:
        if event.latitude is not None and event.longitude is not None:
            return DisplayPoint(
                lat=event.latitude,
                lng=event.longitude,
                source="event",
            )
        return None
