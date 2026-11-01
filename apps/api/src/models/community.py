"""People, organisations, needs, offers and connections (Phase 2).

Phoenix connects organisations that need something with people and
organisations that can provide it. It never holds the location of an
individual (RESPONSIBLE_USE.md §2): a need carries the location of a site
such as a camp or a district, entered by an approved organisation.

Contact details stay private until both sides approve a connection.
"""

from __future__ import annotations

import enum
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.database import Base


def _now() -> datetime:
    return datetime.now(UTC)


class OrgType(str, enum.Enum):
    un = "un"
    international_ngo = "international_ngo"
    local_partner = "local_partner"
    government = "government"
    other = "other"


class OrgStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class MemberRole(str, enum.Enum):
    member = "member"
    org_admin = "org_admin"


class NeedPriority(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class NeedStatus(str, enum.Enum):
    open = "open"
    paused = "paused"
    closed = "closed"


class NeedVisibility(str, enum.Enum):
    public = "public"
    org_only = "org_only"


class OfferType(str, enum.Enum):
    funding = "funding"
    goods = "goods"
    service = "service"
    volunteer = "volunteer"
    transport = "transport"
    other = "other"


class OfferStatus(str, enum.Enum):
    open = "open"
    withdrawn = "withdrawn"
    closed = "closed"


class OfferVisibility(str, enum.Enum):
    public = "public"
    private = "private"


class ConnectStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    canceled = "canceled"


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    # Stored lower-cased; unique
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True)
    display_name: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    memberships: Mapped[list[OrgMembership]] = relationship(back_populates="user")


class MagicLinkToken(Base):
    """One-time login link. Only the SHA-256 of the token is stored."""

    __tablename__ = "magic_link_tokens"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    redirect_path: Mapped[str | None] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (Index("idx_magic_link_email_created", "email", "created_at"),)


class UserSession(Base):
    """Login session. Only the SHA-256 of the session token is stored."""

    __tablename__ = "user_sessions"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship()

    __table_args__ = (Index("idx_user_sessions_user", "user_id"),)


class Org(Base):
    __tablename__ = "orgs"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    org_type: Mapped[OrgType] = mapped_column(Enum(OrgType, name="org_type"), nullable=False)
    status: Mapped[OrgStatus] = mapped_column(
        Enum(OrgStatus, name="org_status"), nullable=False, default=OrgStatus.pending
    )
    # Public contact address for the organisation's needs
    primary_email: Mapped[str] = mapped_column(String(320), nullable=False)
    website: Mapped[str | None] = mapped_column(String(300))
    requested_by_user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    decided_by_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)

    memberships: Mapped[list[OrgMembership]] = relationship(back_populates="org")

    __table_args__ = (Index("idx_orgs_status", "status"),)


class OrgMembership(Base):
    __tablename__ = "org_memberships"

    org_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("orgs.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    role: Mapped[MemberRole] = mapped_column(
        Enum(MemberRole, name="member_role"), nullable=False, default=MemberRole.member
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)

    org: Mapped[Org] = relationship(back_populates="memberships")
    user: Mapped[User] = relationship(back_populates="memberships")

    __table_args__ = (Index("idx_org_memberships_user", "user_id"),)


class Need(Base):
    __tablename__ = "needs"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    event_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("events.id", ondelete="SET NULL")
    )
    org_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    # Standard categories (services/matching.CATEGORIES)
    categories: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    priority: Mapped[NeedPriority] = mapped_column(
        Enum(NeedPriority, name="need_priority"), nullable=False, default=NeedPriority.medium
    )
    quantity: Mapped[int | None] = mapped_column(Integer)
    unit: Mapped[str | None] = mapped_column(String(40))
    beneficiaries: Mapped[int | None] = mapped_column(Integer)
    # Site (camp, district, facility) — never a person
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    place_name: Mapped[str | None] = mapped_column(String(200))
    status: Mapped[NeedStatus] = mapped_column(
        Enum(NeedStatus, name="need_status"), nullable=False, default=NeedStatus.open
    )
    visibility: Mapped[NeedVisibility] = mapped_column(
        Enum(NeedVisibility, name="need_visibility"), nullable=False, default=NeedVisibility.public
    )
    created_by_user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now, nullable=False
    )

    org: Mapped[Org] = relationship()

    __table_args__ = (
        Index("idx_needs_event", "event_id"),
        Index("idx_needs_org", "org_id"),
        Index("idx_needs_status", "status"),
        CheckConstraint("quantity IS NULL OR quantity > 0", name="chk_needs_quantity"),
        CheckConstraint("beneficiaries IS NULL OR beneficiaries >= 0", name="chk_needs_beneficiaries"),
        CheckConstraint("latitude IS NULL OR latitude BETWEEN -90 AND 90", name="chk_needs_lat"),
        CheckConstraint("longitude IS NULL OR longitude BETWEEN -180 AND 180", name="chk_needs_lng"),
    )


class Offer(Base):
    __tablename__ = "offers"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    event_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("events.id", ondelete="SET NULL")
    )
    created_by_user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    offer_type: Mapped[OfferType] = mapped_column(Enum(OfferType, name="offer_type"), nullable=False)
    categories: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    quantity: Mapped[int | None] = mapped_column(Integer)
    unit: Mapped[str | None] = mapped_column(String(40))
    # Where the help is available from (a city or depot), optional
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    place_name: Mapped[str | None] = mapped_column(String(200))
    status: Mapped[OfferStatus] = mapped_column(
        Enum(OfferStatus, name="offer_status"), nullable=False, default=OfferStatus.open
    )
    visibility: Mapped[OfferVisibility] = mapped_column(
        Enum(OfferVisibility, name="offer_visibility"), nullable=False, default=OfferVisibility.public
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now, nullable=False
    )

    creator: Mapped[User] = relationship()

    __table_args__ = (
        Index("idx_offers_event", "event_id"),
        Index("idx_offers_creator", "created_by_user_id"),
        Index("idx_offers_status", "status"),
        CheckConstraint("quantity IS NULL OR quantity > 0", name="chk_offers_quantity"),
        CheckConstraint("latitude IS NULL OR latitude BETWEEN -90 AND 90", name="chk_offers_lat"),
        CheckConstraint("longitude IS NULL OR longitude BETWEEN -180 AND 180", name="chk_offers_lng"),
    )


class Connect(Base):
    """A proposed link between a need and an offer; both sides must approve."""

    __tablename__ = "connects"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    need_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("needs.id", ondelete="CASCADE"), nullable=False
    )
    offer_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("offers.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[ConnectStatus] = mapped_column(
        Enum(ConnectStatus, name="connect_status"), nullable=False, default=ConnectStatus.pending
    )
    message: Mapped[str | None] = mapped_column(Text)
    need_approved_by_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    need_approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    offer_approved_by_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    offer_approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_by_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by_user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)

    need: Mapped[Need] = relationship()
    offer: Mapped[Offer] = relationship()

    __table_args__ = (
        UniqueConstraint("need_id", "offer_id", name="uq_connects_need_offer"),
        Index("idx_connects_offer", "offer_id"),
    )


class Disclosure(Base):
    """Public progress update on an event, published by approved organisations."""

    __tablename__ = "disclosures"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    event_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False
    )
    org_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_by_user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)

    org: Mapped[Org] = relationship()

    __table_args__ = (Index("idx_disclosures_event_created", "event_id", "created_at"),)
