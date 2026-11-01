"""Relief site plans: saved, versioned, forkable, attachable to needs.

A plan is a layout of shared facilities (tents, taps, toilets, health posts,
distribution points) on a site. Every save adds an immutable version, so a
plan's history is kept and others can fork any version to propose changes.
"""

from __future__ import annotations

import enum
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.database import Base


def _now() -> datetime:
    return datetime.now(UTC)


class PlanVisibility(str, enum.Enum):
    public = "public"
    private = "private"


class SitePlan(Base):
    __tablename__ = "site_plans"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    event_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("events.id", ondelete="SET NULL"))
    created_by_user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    forked_from_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("site_plans.id", ondelete="SET NULL")
    )
    forked_from_version: Mapped[int | None] = mapped_column(Integer)
    visibility: Mapped[PlanVisibility] = mapped_column(
        Enum(PlanVisibility, name="plan_visibility"), nullable=False, default=PlanVisibility.public
    )
    latest_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)

    versions: Mapped[list[SitePlanVersion]] = relationship(back_populates="plan", order_by="SitePlanVersion.number")

    __table_args__ = (
        Index("idx_site_plans_event", "event_id"),
        Index("idx_site_plans_creator", "created_by_user_id"),
        Index("idx_site_plans_forked_from", "forked_from_id"),
    )


class SitePlanVersion(Base):
    __tablename__ = "site_plan_versions"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    plan_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("site_plans.id", ondelete="CASCADE"), nullable=False
    )
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    population: Mapped[int] = mapped_column(Integer, nullable=False)
    # [[kind, lat, lng], ...] — compact; kinds as in the web planner
    items: Mapped[list] = mapped_column(JSONB, nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    created_by_user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)

    plan: Mapped[SitePlan] = relationship(back_populates="versions")

    __table_args__ = (
        UniqueConstraint("plan_id", "number", name="uq_site_plan_versions_number"),
        CheckConstraint("population >= 0 AND population <= 1000000", name="chk_site_plan_population"),
    )
