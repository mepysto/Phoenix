"""Repository for DataSource operations."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update

from src.models.event import DataSource
from src.repositories.base import BaseRepository


class DataSourceRepository(BaseRepository):
    """Repository for DataSource CRUD operations."""

    async def get_by_name(self, name: str) -> DataSource | None:
        """Get a data source by its unique name.

        Args:
            name: The unique name of the data source

        Returns:
            DataSource if found, None otherwise
        """
        stmt = select(DataSource).where(DataSource.name == name)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_or_create(
        self,
        *,
        name: str,
        type: str,
        defaults: dict | None = None,
    ) -> DataSource:
        """Get existing data source or create new one.

        Args:
            name: The unique name of the data source
            type: The type of data source (e.g., 'disaster_alert', 'satellite')
            defaults: Optional additional fields to set on creation

        Returns:
            Existing or newly created DataSource
        """
        existing = await self.get_by_name(name)
        if existing is not None:
            return existing

        # Create new data source
        data = {"name": name, "type": type}
        if defaults:
            data.update(defaults)

        source = DataSource(**data)
        self.session.add(source)
        await self.session.flush()
        return source

    async def update_sync_status(
        self,
        source_id: UUID,
        *,
        last_sync: datetime,
        status: str,
        error: str | None = None,
    ) -> None:
        """Update the sync status of a data source.

        Args:
            source_id: The UUID of the data source
            last_sync: Timestamp of the sync attempt
            status: Status of the sync ('success', 'failed', etc.)
            error: Optional error message if sync failed
        """
        update_data: dict = {
            "last_sync": last_sync,
            "last_sync_status": status,
        }

        if status == "success":
            update_data["consecutive_failures"] = 0
            update_data["last_sync_error"] = None
        elif status == "failed":
            update_data["last_sync_error"] = error
            # Increment consecutive failures using raw SQL
            stmt = (
                update(DataSource)
                .where(DataSource.id == source_id)
                .values(
                    last_sync=last_sync,
                    last_sync_status=status,
                    last_sync_error=error,
                    consecutive_failures=DataSource.consecutive_failures + 1,
                )
            )
            await self.session.execute(stmt)
            return

        stmt = (
            update(DataSource)
            .where(DataSource.id == source_id)
            .values(**update_data)
        )
        await self.session.execute(stmt)

    async def get_by_id(self, source_id: UUID) -> DataSource | None:
        """Get a data source by its ID.

        Args:
            source_id: The UUID of the data source

        Returns:
            DataSource if found, None otherwise
        """
        stmt = select(DataSource).where(DataSource.id == source_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_active(self) -> list[DataSource]:
        """List all active data sources.

        Returns:
            List of active DataSource objects
        """
        stmt = select(DataSource).where(DataSource.is_active.is_(True))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
