"""AdminArea model for administrative boundaries (countries, states, etc)."""

from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.database import Base

if TYPE_CHECKING:
    from src.models.event import Event


class AdminArea(Base):
    """Administrative area model for geographic boundaries.

    Represents hierarchical administrative divisions from countries (level 0)
    down to local districts. Uses PostGIS geometry types for spatial queries.

    Attributes:
        id: Unique identifier (UUID)
        iso_a2: ISO 3166-1 alpha-2 code (e.g., KR, US) - only for countries
        iso_a3: ISO 3166-1 alpha-3 code (e.g., KOR, USA) - only for countries
        name: English name of the area
        name_local: Local language name (nullable)
        admin_level: Hierarchy level (0=country, 1=state/province, etc.)
        parent_id: Reference to parent administrative area
        geometry: MultiPolygon boundary geometry (SRID 4326)
        centroid: Point centroid of the area (SRID 4326)
        bbox: Bounding box as JSONB {minx, miny, maxx, maxy}
        population: Estimated population (nullable)
        created_at: Timestamp of record creation
        updated_at: Timestamp of last update
    """

    __tablename__ = "admin_areas"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    iso_a2: Mapped[str | None] = mapped_column(String(2))
    iso_a3: Mapped[str | None] = mapped_column(String(3))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    name_local: Mapped[str | None] = mapped_column(String(255))
    admin_level: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Self-referential relationship for hierarchy
    parent_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("admin_areas.id")
    )

    # PostGIS geometry columns
    geometry = mapped_column(Geometry("MULTIPOLYGON", srid=4326), nullable=True)
    centroid = mapped_column(Geometry("POINT", srid=4326), nullable=True)

    # Bounding box as JSONB: {minx, miny, maxx, maxy}
    bbox: Mapped[dict | None] = mapped_column(JSONB)

    population: Mapped[int | None] = mapped_column(Integer)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    events: Mapped[list["Event"]] = relationship(back_populates="admin_area")
    parent: Mapped["AdminArea | None"] = relationship(
        "AdminArea",
        remote_side="AdminArea.id",
        back_populates="children",
        foreign_keys=[parent_id],
    )
    children: Mapped[list["AdminArea"]] = relationship(
        "AdminArea",
        back_populates="parent",
        foreign_keys=[parent_id],
    )

    __table_args__ = (
        # Unique ISO codes for countries (admin_level = 0)
        Index(
            "idx_admin_areas_iso_a2",
            "iso_a2",
            unique=True,
            postgresql_where="admin_level = 0 AND iso_a2 IS NOT NULL",
        ),
        Index(
            "idx_admin_areas_iso_a3",
            "iso_a3",
            unique=True,
            postgresql_where="admin_level = 0 AND iso_a3 IS NOT NULL",
        ),
        # Spatial index on geometry
        Index("idx_admin_areas_geometry", "geometry", postgresql_using="gist"),
        # Parent lookup index
        Index("idx_admin_areas_parent", "parent_id"),
        # Admin level index for hierarchy queries
        Index("idx_admin_areas_level", "admin_level"),
    )

    def __repr__(self) -> str:
        return f"<AdminArea(id={self.id}, name={self.name}, level={self.admin_level})>"
