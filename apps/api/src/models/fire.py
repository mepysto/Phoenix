"""Satellite active-fire detections (NASA LANCE FIRMS)."""

from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import BigInteger, DateTime, Float, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from src.db.database import Base


class FireDetection(Base):
    """One thermal anomaly seen by one satellite pass.

    Rows older than FIRMS_RETENTION_HOURS are pruned on every ingest; the
    unique key makes re-reading the rolling 24 h files idempotent.
    """

    __tablename__ = "fire_detections"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    satellite: Mapped[str] = mapped_column(String(16), nullable=False)  # N, N20, T, A
    instrument: Mapped[str] = mapped_column(String(8), nullable=False)  # VIIRS | MODIS
    acquired_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    # Fire radiative power (MW): the best single measure of fire intensity
    frp: Mapped[float | None] = mapped_column(Float)
    brightness_k: Mapped[float | None] = mapped_column(Float)
    confidence: Mapped[str | None] = mapped_column(String(16))  # low/nominal/high or 0-100
    daynight: Mapped[str | None] = mapped_column(String(1))
    location = mapped_column(Geometry("POINT", srid=4326), nullable=False)

    __table_args__ = (
        Index(
            "idx_fire_detections_identity",
            "satellite",
            "acquired_at",
            "latitude",
            "longitude",
            unique=True,
        ),
        Index("idx_fire_detections_acquired_at", "acquired_at"),
    )
