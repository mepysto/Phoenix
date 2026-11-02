"""Design challenges: organisations ask for site plans, people submit and vote.

PRD scenario 2 ("recovery design hackathon"): an approved organisation
opens a challenge for a site, anyone submits a public site plan, signed-in
users vote, and the host selects an entry to take forward.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.database import Base


def _now() -> datetime:
    return datetime.now(UTC)


class Challenge(Base):
    __tablename__ = "challenges"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    org_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False)
    event_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("events.id", ondelete="SET NULL"))
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    brief: Mapped[str] = mapped_column(Text, nullable=False)
    population: Mapped[int] = mapped_column(Integer, nullable=False)
    closes_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    selected_entry_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("challenge_entries.id", ondelete="SET NULL", use_alter=True, name="fk_challenges_selected_entry")
    )
    created_by_user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)

    entries: Mapped[list[ChallengeEntry]] = relationship(
        back_populates="challenge", foreign_keys="ChallengeEntry.challenge_id"
    )

    __table_args__ = (
        Index("idx_challenges_event", "event_id"),
        Index("idx_challenges_closes_at", "closes_at"),
        CheckConstraint("population > 0 AND population <= 1000000", name="chk_challenges_population"),
    )


class ChallengeEntry(Base):
    __tablename__ = "challenge_entries"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    challenge_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("challenges.id", ondelete="CASCADE"), nullable=False
    )
    plan_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("site_plans.id", ondelete="CASCADE"), nullable=False)
    submitted_by_user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)

    challenge: Mapped[Challenge] = relationship(back_populates="entries", foreign_keys=[challenge_id])

    __table_args__ = (UniqueConstraint("challenge_id", "plan_id", name="uq_challenge_entries_plan"),)


class ChallengeVote(Base):
    __tablename__ = "challenge_votes"

    entry_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("challenge_entries.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)

    __table_args__ = (Index("idx_challenge_votes_user", "user_id"),)
