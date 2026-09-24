"""Critical infrastructure (dams, power plants) from open reference datasets."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, Float, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.db.database import Base


class InfrastructureAsset(Base):
    """A fixed asset whose failure can cascade (dam break, blackout).

    Loaded by scripts/import_infrastructure.py; `(source, source_id)` is
    unique so re-imports update rows in place.
    """

    __tablename__ = "infrastructure_assets"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)  # dam | power_plant
    name: Mapped[str | None] = mapped_column(String(255))
    country: Mapped[str | None] = mapped_column(String(100))
    # Ranking for "show the most significant first" (MW for plants, m for dams)
    importance: Mapped[float | None] = mapped_column(Float)
    attributes: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    location = mapped_column(Geometry("POINT", srid=4326), nullable=False)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    source_id: Mapped[str] = mapped_column(String(128), nullable=False)
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    __table_args__ = (
        Index("idx_infrastructure_source_ref", "source", "source_id", unique=True),
        Index("idx_infrastructure_kind_importance", "kind", "importance"),
    )
