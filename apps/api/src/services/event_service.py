"""Event service for managing disaster events with DB integration."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.event import Event
from src.repositories.event_repository import EventRepository
from src.schemas.event import (
    DataSourceRef,
    EventDetailResponse,
    EventFilter,
    EventListResponse,
    EventResponse,
    GeoLayerResponse,
    Location,
    Pagination,
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
        """Get event layers (Phase 2: returns empty list).

        Args:
            event_id: UUID of the event

        Returns:
            Empty list for Phase 2
        """
        return []

    def _to_response(self, event: Event) -> EventResponse:
        """Convert Event model to EventResponse schema.

        Args:
            event: Event SQLAlchemy model

        Returns:
            EventResponse Pydantic schema
        """
        # Create Location from event fields
        location = Location(
            lat=event.latitude if event.latitude is not None else 0.0,
            lng=event.longitude if event.longitude is not None else 0.0,
            country=event.region,
            country_code=event.country_code,
        )

        # Build sources list from relationship (eagerly loaded)
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
            # If lazy loading fails in async context, return empty sources
            pass

        return EventResponse(
            id=event.id,
            type=event.type.value,
            title=event.title,
            description=event.description,
            location=location,
            severity=event.severity.value,
            affected_population=event.affected_population,
            start_date=event.start_date,
            end_date=event.end_date,
            is_active=event.is_active,
            sources=sources,
            created_at=event.created_at,
            updated_at=event.updated_at,
        )
