"""Latest AIS position per ship near active disasters (AISStream)."""

from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import BigInteger, DateTime, Float, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.db.database import Base


class VesselPosition(Base):
    """One row per ship (MMSI), overwritten by each report; old rows are pruned."""

    __tablename__ = "vessel_positions"

    mmsi: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str | None] = mapped_column(String(32))
    ship_type: Mapped[int | None] = mapped_column(Integer)  # AIS type code (e.g. 30 fishing, 60-69 passenger)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    speed_kn: Mapped[float | None] = mapped_column(Float)
    course_deg: Mapped[float | None] = mapped_column(Float)
    heading_deg: Mapped[float | None] = mapped_column(Float)
    location = mapped_column(Geometry("POINT", srid=4326, spatial_index=False), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index("idx_vessel_positions_updated_at", "updated_at"),
        Index("idx_vessel_positions_location", "location", postgresql_using="gist"),
    )
