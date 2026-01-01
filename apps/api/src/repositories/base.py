"""Base repository class for database operations."""

from sqlalchemy.ext.asyncio import AsyncSession


class BaseRepository:
    """Base repository providing common database session handling."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session.

        Args:
            session: SQLAlchemy async session for database operations
        """
        self.session = session
