"""Repository for EventSource operations."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from src.models.event import EventSource
from src.repositories.base import BaseRepository


class EventSourceRepository(BaseRepository):
    """Repository for EventSource CRUD operations with upsert support."""

    async def upsert(
        self,
        *,
        source_id: UUID,
        external_id: str,
        event_id: UUID,
        raw_data: dict,
        fetched_at: datetime,
    ) -> EventSource:
        """Insert or update an event source record.

        Uses PostgreSQL ON CONFLICT to upsert based on unique index
        (source_id, external_id).

        Args:
            source_id: UUID of the data source
            external_id: External identifier from the source
            event_id: UUID of the associated event
            raw_data: Raw JSON data from the source
            fetched_at: Timestamp when data was fetched

        Returns:
            The upserted EventSource record
        """
        stmt = insert(EventSource).values(
            source_id=source_id,
            external_id=external_id,
            event_id=event_id,
            raw_data=raw_data,
            fetched_at=fetched_at,
        )

        # On conflict, update the mutable fields
        stmt = stmt.on_conflict_do_update(
            index_elements=["source_id", "external_id"],
            set_={
                "event_id": stmt.excluded.event_id,
                "raw_data": stmt.excluded.raw_data,
                "fetched_at": stmt.excluded.fetched_at,
            },
        )

        # Return the upserted row
        stmt = stmt.returning(EventSource)
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def find_event_id_by_source_external(
        self,
        *,
        source_id: UUID,
        external_id: str,
    ) -> UUID | None:
        """Find the event ID for a given source and external ID.

        Args:
            source_id: UUID of the data source
            external_id: External identifier from the source

        Returns:
            Event UUID if found, None otherwise
        """
        stmt = select(EventSource.event_id).where(
            EventSource.source_id == source_id,
            EventSource.external_id == external_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_source_external(
        self,
        *,
        source_id: UUID,
        external_id: str,
    ) -> EventSource | None:
        """Get an EventSource by source ID and external ID.

        Args:
            source_id: UUID of the data source
            external_id: External identifier from the source

        Returns:
            EventSource if found, None otherwise
        """
        stmt = select(EventSource).where(
            EventSource.source_id == source_id,
            EventSource.external_id == external_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_event(self, event_id: UUID) -> list[EventSource]:
        """List all EventSources for a given event.

        Args:
            event_id: UUID of the event

        Returns:
            List of EventSource objects
        """
        stmt = select(EventSource).where(EventSource.event_id == event_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
