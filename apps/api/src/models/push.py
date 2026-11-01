"""Browser push subscriptions for closed-tab area alerts.

Opt-in only. A subscription holds the push service endpoint and keys the
browser gave us, and the watch areas rounded to ~10 km. It is not linked to
an account; deleting it (turning alerts off) removes the areas.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.db.database import Base


def _now() -> datetime:
    return datetime.now(UTC)


class PushSubscription(Base):
    __tablename__ = "push_subscriptions"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    endpoint: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    p256dh: Mapped[str] = mapped_column(String(120), nullable=False)
    auth: Mapped[str] = mapped_column(String(40), nullable=False)
    # [{"name", "lat", "lng", "radius_km", "min_severity"}]
    areas: Mapped[list] = mapped_column(JSONB, nullable=False)
    lang: Mapped[str] = mapped_column(String(5), nullable=False, default="en")
    failures: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)


class PushDelivery(Base):
    """One alert sent for one event to one subscription — never twice."""

    __tablename__ = "push_deliveries"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    subscription_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("push_subscriptions.id", ondelete="CASCADE"), nullable=False
    )
    event_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("subscription_id", "event_id", name="uq_push_deliveries"),
        Index("idx_push_deliveries_sent_at", "sent_at"),
    )
