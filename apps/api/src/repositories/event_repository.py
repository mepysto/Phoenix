"""Repository for Event operations."""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.orm import selectinload

from src.models.event import Event, EventSource, EventType, GeoPrecision, SeverityLevel
from src.repositories.base import BaseRepository
from src.schemas.event import EventFilter
from src.utils.geo import make_point_expr, point_within_distance, validate_lat_lng

# GeoPrecision ranking for comparison (higher = better)
GEO_PRECISION_RANK: dict[GeoPrecision, int] = {
    GeoPrecision.unknown: 0,
    GeoPrecision.country: 1,
    GeoPrecision.admin1: 2,
    GeoPrecision.approximate: 3,
    GeoPrecision.exact: 4,
}


def _pop_coord(data: dict[str, Any], short: str, long: str) -> Any:
    """Pop a coordinate by short or long key, treating 0.0 as a valid value."""
    short_val = data.pop(short, None)
    long_val = data.pop(long, None)
    return short_val if short_val is not None else long_val


# Fields that may legitimately be cleared to None by a source refresh
NULLABLE_REFRESH_FIELDS = frozenset({"end_date"})


class EventRepository(BaseRepository):
    """Repository for Event CRUD operations."""

    async def create(self, **kwargs: Any) -> Event:
        """Create a new event.

        Automatically converts lat/lng to PostGIS POINT geometry.

        Args:
            **kwargs: Event fields including lat, lng, type, title, etc.

        Returns:
            The created Event
        """
        # Extract lat/lng for PostGIS conversion
        lat = _pop_coord(kwargs, "lat", "latitude")
        lng = _pop_coord(kwargs, "lng", "longitude")

        # Convert string enum values to proper enum types if needed
        if "type" in kwargs and isinstance(kwargs["type"], str):
            kwargs["type"] = EventType(kwargs["type"])
        if "severity" in kwargs and isinstance(kwargs["severity"], str):
            kwargs["severity"] = SeverityLevel(kwargs["severity"])
        if "geo_precision" in kwargs and isinstance(kwargs["geo_precision"], str):
            kwargs["geo_precision"] = GeoPrecision(kwargs["geo_precision"])

        # Create event with lat/lng
        if validate_lat_lng(lat, lng):
            kwargs["latitude"] = lat
            kwargs["longitude"] = lng
            # Create PostGIS POINT geometry
            kwargs["location"] = make_point_expr(lat, lng)

        event = Event(**kwargs)
        self.session.add(event)
        await self.session.flush()
        return event

    async def update(
        self,
        event_id: UUID,
        **kwargs: Any,
    ) -> Event | None:
        """Update event with given fields.

        Args:
            event_id: UUID of the event to update
            **kwargs: Fields to update

        Returns:
            Updated Event if found, None otherwise
        """
        # Handle lat/lng conversion
        lat = _pop_coord(kwargs, "lat", "latitude")
        lng = _pop_coord(kwargs, "lng", "longitude")

        if validate_lat_lng(lat, lng):
            kwargs["latitude"] = lat
            kwargs["longitude"] = lng
            kwargs["location"] = make_point_expr(lat, lng)

        # Convert string enum values
        if "type" in kwargs and isinstance(kwargs["type"], str):
            kwargs["type"] = EventType(kwargs["type"])
        if "severity" in kwargs and isinstance(kwargs["severity"], str):
            kwargs["severity"] = SeverityLevel(kwargs["severity"])
        if "geo_precision" in kwargs and isinstance(kwargs["geo_precision"], str):
            kwargs["geo_precision"] = GeoPrecision(kwargs["geo_precision"])

        if not kwargs:
            return await self.get_by_id(event_id)

        # Ensure updated_at is set
        if "updated_at" not in kwargs:
            kwargs["updated_at"] = datetime.now(UTC)

        # One round trip; populate_existing refreshes an already-loaded Event
        # in the session so callers never see stale attribute values.
        stmt = (
            update(Event)
            .where(Event.id == event_id)
            .values(**kwargs)
            .returning(Event)
            .execution_options(populate_existing=True)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_if_better(
        self,
        event_id: UUID,
        patch: dict[str, Any],
    ) -> Event | None:
        """Refresh an event from its own source.

        Status/descriptive fields (title, severity, end_date, is_active, ...)
        are always applied so that source-side changes (e.g. an event closing)
        propagate. Location fields are applied only when the incoming
        geo_precision is at least as good as the current one.

        Args:
            event_id: UUID of the event to update
            patch: Dictionary of fields to update

        Returns:
            Updated Event if any field changed, None otherwise
        """
        event = await self.get_by_id(event_id)
        if event is None:
            return None

        patch = dict(patch)
        lat = _pop_coord(patch, "lat", "latitude")
        lng = _pop_coord(patch, "lng", "longitude")

        new_precision = patch.pop("geo_precision", None)
        if isinstance(new_precision, str):
            new_precision = GeoPrecision(new_precision)
        geo_method = patch.pop("geo_method", None)

        current_rank = GEO_PRECISION_RANK.get(event.geo_precision or GeoPrecision.unknown, 0)
        new_rank = GEO_PRECISION_RANK.get(new_precision, 0) if new_precision else current_rank
        location_ok = new_rank >= current_rank and validate_lat_lng(lat, lng)
        if location_ok:
            patch["latitude"] = lat
            patch["longitude"] = lng
            if new_precision is not None:
                patch["geo_precision"] = new_precision
            if geo_method is not None:
                patch["geo_method"] = geo_method

        if "type" in patch and isinstance(patch["type"], str):
            patch["type"] = EventType(patch["type"])
        if "severity" in patch and isinstance(patch["severity"], str):
            patch["severity"] = SeverityLevel(patch["severity"])

        # Keep only real changes; a refresh never erases data with None
        changes = {
            key: value
            for key, value in patch.items()
            if (value is not None or key in NULLABLE_REFRESH_FIELDS)
            and getattr(event, key, None) != value
        }
        if "latitude" in changes or "longitude" in changes:
            changes["location"] = make_point_expr(lat, lng)
        if not changes:
            return None

        changes["updated_at"] = datetime.now(UTC)
        stmt = update(Event).where(Event.id == event_id).values(**changes)
        await self.session.execute(stmt)
        await self.session.flush()
        return await self.get_by_id(event_id)

    async def list_events(
        self,
        filters: EventFilter,
        limit: int,
        offset: int,
        with_sources: bool = False,
    ) -> tuple[list[Event], int]:
        """List events with filtering and pagination.

        Args:
            filters: EventFilter with optional type, severity, date, bbox filters
            limit: Maximum number of events to return
            offset: Number of events to skip
            with_sources: If True, eagerly load sources relationship

        Returns:
            Tuple of (list of Events, total count)
        """
        # Base query
        stmt = select(Event)
        count_stmt = select(func.count(Event.id))

        # Optionally eager load sources
        if with_sources:
            stmt = stmt.options(
                selectinload(Event.sources).selectinload(EventSource.source)
            )

        # Apply filters
        conditions = []

        if filters.types:
            type_enums = [EventType(t) for t in filters.types]
            conditions.append(Event.type.in_(type_enums))

        if filters.severities:
            severity_enums = [SeverityLevel(s) for s in filters.severities]
            conditions.append(Event.severity.in_(severity_enums))

        if filters.is_active is not None:
            conditions.append(Event.is_active == filters.is_active)

        if not filters.include_merged:
            conditions.append(Event.is_canonical.is_(True))

        if filters.start_date:
            conditions.append(Event.start_date >= filters.start_date)

        if filters.end_date:
            conditions.append(Event.start_date <= filters.end_date)

        # Bounding box filter
        if all(
            v is not None
            for v in [filters.min_lng, filters.min_lat, filters.max_lng, filters.max_lat]
        ):
            conditions.append(Event.longitude >= filters.min_lng)
            conditions.append(Event.longitude <= filters.max_lng)
            conditions.append(Event.latitude >= filters.min_lat)
            conditions.append(Event.latitude <= filters.max_lat)

        center_lat = filters.center_lat
        center_lng = filters.center_lng
        radius_km = filters.radius_km
        if center_lat is not None and center_lng is not None and radius_km is not None:
            radius_meters = int(radius_km * 1000)
            conditions.append(Event.location.isnot(None))
            conditions.append(
                point_within_distance(
                    Event.location,
                    center_lat,
                    center_lng,
                    radius_meters,
                )
            )

        # Apply all conditions
        for condition in conditions:
            stmt = stmt.where(condition)
            count_stmt = count_stmt.where(condition)

        # Order and pagination
        stmt = stmt.order_by(Event.start_date.desc())
        stmt = stmt.limit(limit).offset(offset)

        # Execute queries
        result = await self.session.execute(stmt)
        events = list(result.scalars().all())

        count_result = await self.session.execute(count_stmt)
        total = count_result.scalar_one()

        return events, total

    async def get_by_id(self, event_id: UUID) -> Event | None:
        """Get an event by its ID.

        Args:
            event_id: UUID of the event

        Returns:
            Event if found, None otherwise
        """
        stmt = select(Event).where(Event.id == event_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id_with_sources(self, event_id: UUID) -> Event | None:
        """Get an event by its ID with sources eagerly loaded.

        Args:
            event_id: UUID of the event

        Returns:
            Event with sources loaded if found, None otherwise
        """
        stmt = (
            select(Event)
            .where(Event.id == event_id)
            .options(
                selectinload(Event.sources).selectinload(EventSource.source)
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_source_id(self, source_id: str) -> Event | None:
        """Get an event by its legacy source_id field.

        Args:
            source_id: The source_id string

        Returns:
            Event if found, None otherwise
        """
        stmt = select(Event).where(Event.source_id == source_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_active(self, limit: int = 100) -> list[Event]:
        """List active events.

        Args:
            limit: Maximum number of events to return

        Returns:
            List of active Event objects
        """
        stmt = (
            select(Event)
            .where(Event.is_active.is_(True))
            .order_by(Event.start_date.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def deactivate(self, event_id: UUID) -> None:
        """Mark an event as inactive.

        Args:
            event_id: UUID of the event to deactivate
        """
        stmt = (
            update(Event)
            .where(Event.id == event_id)
            .values(is_active=False, updated_at=datetime.now(UTC))
        )
        await self.session.execute(stmt)

    async def find_candidates_by_spatiotemporal(
        self,
        *,
        event_type: EventType,
        lat: float,
        lng: float,
        start_date: datetime,
        radius_meters: int = 50_000,
        window_hours: int = 48,
    ) -> list[Event]:
        """Search candidate events by spatiotemporal criteria.

        Finds events matching:
        - Same event type
        - Within radius_meters of the given point (ST_DWithin)
        - Within window_hours of the given start_date

        Args:
            event_type: Event type to match
            lat: Reference point latitude
            lng: Reference point longitude
            start_date: Reference date for time window
            radius_meters: Search radius in meters (default 50km)
            window_hours: Time window in hours (default 48h)

        Returns:
            List of matching Events with sources relationship loaded
        """
        time_delta = timedelta(hours=window_hours)
        min_date = start_date - time_delta
        max_date = start_date + time_delta

        stmt = (
            select(Event)
            .where(Event.type == event_type)
            .where(Event.is_canonical.is_(True))
            .where(Event.location.isnot(None))
            .where(point_within_distance(Event.location, lat, lng, radius_meters))
            .where(Event.start_date >= min_date)
            .where(Event.start_date <= max_date)
            .options(selectinload(Event.sources).selectinload(EventSource.source))
            .order_by(Event.start_date.desc())
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def find_by_glide_number(self, glide_number: str) -> Event | None:
        """Find an event by its GLIDE number.

        Args:
            glide_number: GLIDE code (e.g., DR-2024-000001-PHL)

        Returns:
            Matching Event or None if not found
        """
        stmt = (
            select(Event)
            .where(Event.glide_number == glide_number)
            .where(Event.is_canonical.is_(True))
            .options(selectinload(Event.sources).selectinload(EventSource.source))
            .order_by(Event.created_at)
            .limit(1)
        )
        result = await self.session.execute(stmt)
        # Legacy data may hold several events per GLIDE; take the oldest canonical one
        return result.scalars().first()
