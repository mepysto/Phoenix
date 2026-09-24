"""Read-only queries about what the map currently shows (G-5)."""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from src.models.event import Event, EventSource
from src.repositories.base import BaseRepository
from src.repositories.event_repository import event_filter_conditions
from src.schemas.event import EventFilter
from src.utils.geo import distance_meters, point_within_distance


class EventViewRepository(BaseRepository):
    async def summarize(
        self, filters: EventFilter
    ) -> tuple[dict[tuple[str, str], int], int, datetime | None]:
        """Counts per (type, severity), affected population sum, latest update."""
        conditions = event_filter_conditions(filters)
        rows = (
            await self.session.execute(
                select(Event.type, Event.severity, func.count())
                .where(*conditions)
                .group_by(Event.type, Event.severity)
            )
        ).all()
        population, last_updated = (
            await self.session.execute(
                select(func.coalesce(func.sum(Event.affected_population), 0), func.max(Event.updated_at))
                .where(*conditions)
            )
        ).one()
        counts = {(t.value, s.value): n for t, s, n in rows}
        return counts, int(population), last_updated

    async def nearest(
        self, filters: EventFilter, lat: float, lng: float, radius_km: float, limit: int
    ) -> list[tuple[Event, float]]:
        """Events within radius_km of a point, nearest first, with distance in metres."""
        distance = distance_meters(Event.location, lat, lng)
        stmt = (
            select(Event, distance)
            .where(*event_filter_conditions(filters))
            .where(Event.location.isnot(None))
            .where(point_within_distance(Event.location, lat, lng, int(radius_km * 1000)))
            .order_by(distance)
            .limit(limit)
            .options(selectinload(Event.sources).selectinload(EventSource.source))
        )
        return [(event, float(meters)) for event, meters in (await self.session.execute(stmt)).all()]
