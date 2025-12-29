import enum
from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.database import Base


class EventType(str, enum.Enum):
    earthquake = "earthquake"
    flood = "flood"
    wildfire = "wildfire"
    hurricane = "hurricane"
    tsunami = "tsunami"
    volcano = "volcano"
    war = "war"
    pollution = "pollution"
    drought = "drought"
    other = "other"


class SeverityLevel(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class Event(Base):
    __tablename__ = "events"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    type: Mapped[EventType] = mapped_column(
        Enum(EventType, name="event_type", create_type=False), nullable=False
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    severity: Mapped[SeverityLevel] = mapped_column(
        Enum(SeverityLevel, name="severity_level", create_type=False),
        nullable=False,
        default=SeverityLevel.medium,
    )
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    affected_area_geojson: Mapped[str | None] = mapped_column(Text)
    country_code: Mapped[str | None] = mapped_column(String(2))
    region: Mapped[str | None] = mapped_column(String(255))
    affected_population: Mapped[int | None] = mapped_column(Integer)
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    source_id: Mapped[str | None] = mapped_column(String(255))
    source_url: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    sources: Mapped[list["EventSource"]] = relationship(back_populates="event")
    layers: Mapped[list["GeoLayer"]] = relationship(back_populates="event")
    datasets: Mapped[list["Dataset"]] = relationship(back_populates="event")

    __table_args__ = (
        Index("idx_events_lat_lon", "latitude", "longitude"),
        Index("idx_events_type", "type"),
        Index("idx_events_severity", "severity"),
        Index("idx_events_start_date", "start_date"),
        Index("idx_events_is_active", "is_active"),
        Index("idx_events_source_id", "source_id"),
    )


class DataSource(Base):
    __tablename__ = "data_sources"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    api_url: Mapped[str | None] = mapped_column(Text)
    api_key_required: Mapped[bool] = mapped_column(Boolean, default=False)
    update_frequency: Mapped[str | None] = mapped_column(String(50))
    last_sync: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB)

    event_sources: Mapped[list["EventSource"]] = relationship(back_populates="source")


class EventSource(Base):
    __tablename__ = "event_sources"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    event_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE")
    )
    source_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("data_sources.id")
    )
    external_id: Mapped[str | None] = mapped_column(String(255))
    raw_data: Mapped[dict | None] = mapped_column(JSONB)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    event: Mapped["Event"] = relationship(back_populates="sources")
    source: Mapped["DataSource"] = relationship(back_populates="event_sources")


class GeoLayer(Base):
    __tablename__ = "geo_layers"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    event_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE")
    )
    layer_type: Mapped[str] = mapped_column(String(100), nullable=False)
    geojson: Mapped[str] = mapped_column(Text, nullable=False)
    properties: Mapped[dict | None] = mapped_column(JSONB)
    timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    event: Mapped["Event"] = relationship(back_populates="layers")

    __table_args__ = (Index("idx_geo_layers_event_id", "event_id"),)


class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    event_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    type: Mapped[str | None] = mapped_column(String(100))
    url: Mapped[str | None] = mapped_column(Text)
    license: Mapped[str | None] = mapped_column(String(255))
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    event: Mapped["Event"] = relationship(back_populates="datasets")


class EventMetric(Base):
    __tablename__ = "event_metrics"

    time: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    event_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), primary_key=True
    )
    metric_type: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[float] = mapped_column(Float, nullable=False)

    __table_args__ = (Index("idx_event_metrics_event_id", "event_id", "time"),)
