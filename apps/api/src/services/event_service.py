from datetime import datetime, timezone
from uuid import UUID, uuid4

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
    async def list_events(
        self, filters: EventFilter, limit: int, offset: int
    ) -> EventListResponse:
        mock_events = self._get_mock_events()

        filtered = mock_events
        if filters.types:
            filtered = [e for e in filtered if e.type in filters.types]
        if filters.severities:
            filtered = [e for e in filtered if e.severity in filters.severities]
        if filters.is_active is not None:
            filtered = [e for e in filtered if e.is_active == filters.is_active]

        total = len(filtered)
        paginated = filtered[offset : offset + limit]

        return EventListResponse(
            data=paginated,
            pagination=Pagination(
                total=total, limit=limit, offset=offset, has_more=offset + limit < total
            ),
        )

    async def get_event(self, event_id: UUID) -> EventDetailResponse | None:
        mock_events = self._get_mock_events()
        for event in mock_events:
            if event.id == event_id:
                return EventDetailResponse(
                    **event.model_dump(), layers=[], datasets=[], metrics=[]
                )
        return None

    async def get_event_layers(self, event_id: UUID) -> list[GeoLayerResponse]:
        return []

    def _get_mock_events(self) -> list[EventResponse]:
        now = datetime.now(timezone.utc)
        return [
            EventResponse(
                id=uuid4(),
                type="earthquake",
                title="M 6.2 Earthquake - Turkey",
                description="Moderate earthquake struck southeastern Turkey",
                location=Location(lat=37.5, lng=37.0, country="Turkey", country_code="TR"),
                severity="high",
                affected_population=50000,
                start_date=now,
                is_active=True,
                sources=[DataSourceRef(id=uuid4(), name="GDACS", type="disaster_alert")],
                created_at=now,
                updated_at=now,
            ),
            EventResponse(
                id=uuid4(),
                type="flood",
                title="Severe Flooding - Bangladesh",
                description="Monsoon flooding affecting multiple districts",
                location=Location(lat=23.8, lng=90.4, country="Bangladesh", country_code="BD"),
                severity="critical",
                affected_population=200000,
                start_date=now,
                is_active=True,
                sources=[DataSourceRef(id=uuid4(), name="GDACS", type="disaster_alert")],
                created_at=now,
                updated_at=now,
            ),
            EventResponse(
                id=uuid4(),
                type="wildfire",
                title="Wildfire - California, USA",
                description="Large wildfire burning in northern California",
                location=Location(
                    lat=39.5, lng=-121.5, country="United States", country_code="US"
                ),
                severity="high",
                affected_population=10000,
                start_date=now,
                is_active=True,
                sources=[DataSourceRef(id=uuid4(), name="GDACS", type="disaster_alert")],
                created_at=now,
                updated_at=now,
            ),
        ]
