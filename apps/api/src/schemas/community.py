"""Request and response models for accounts, orgs, needs, offers, connects."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from src.models.community import (
    ConnectStatus,
    MemberRole,
    NeedPriority,
    NeedStatus,
    NeedVisibility,
    OfferStatus,
    OfferType,
    OfferVisibility,
    OrgStatus,
    OrgType,
)
from src.services.community.matching import CATEGORIES, clean_categories

Category = Literal[
    "shelter",
    "water",
    "sanitation",
    "food",
    "health",
    "power",
    "communications",
    "logistics",
    "education",
    "protection",
    "cash",
    "other",
]
assert set(Category.__args__) == set(CATEGORIES)  # type: ignore[attr-defined]


# --- auth ---------------------------------------------------------------


class LoginLinkRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    redirect_path: str | None = Field(default=None, max_length=300)


class LoginLinkResponse(BaseModel):
    sent: bool = True
    # Only when AUTH_DEV_RETURN_LINK is on outside production
    dev_link: str | None = None


class VerifyRequest(BaseModel):
    token: str = Field(min_length=20, max_length=200)


class OrgSummary(BaseModel):
    id: UUID
    name: str
    org_type: OrgType
    status: OrgStatus
    website: str | None = None
    # Official partner, verified by the platform
    verified: bool = False


class Membership(BaseModel):
    org: OrgSummary
    role: MemberRole


class Me(BaseModel):
    id: UUID
    email: str
    display_name: str | None = None
    is_platform_admin: bool
    memberships: list[Membership]


class SessionResponse(BaseModel):
    user: Me
    redirect_path: str


class MeUpdate(BaseModel):
    display_name: str | None = Field(default=None, max_length=120)


# --- orgs -----------------------------------------------------------------


class OrgCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    org_type: OrgType
    primary_email: str = Field(min_length=3, max_length=320)
    website: str | None = Field(default=None, max_length=300)

    @field_validator("website")
    @classmethod
    def website_is_http(cls, v: str | None) -> str | None:
        if v and not v.startswith(("https://", "http://")):
            raise ValueError("Website must start with https://")
        return v or None


class OrgAdminView(OrgSummary):
    primary_email: str
    requested_by_email: str
    created_at: datetime
    rejection_reason: str | None = None


class OrgDecision(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


class MemberAdd(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    role: MemberRole = MemberRole.member


# --- needs ----------------------------------------------------------------


class _Site(BaseModel):
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    place_name: str | None = Field(default=None, max_length=200)


class NeedCreate(_Site):
    org_id: UUID
    event_id: UUID | None = None
    title: str = Field(min_length=3, max_length=200)
    description: str | None = Field(default=None, max_length=4000)
    categories: list[Category] = Field(min_length=1, max_length=6)
    priority: NeedPriority = NeedPriority.medium
    quantity: int | None = Field(default=None, gt=0)
    unit: str | None = Field(default=None, max_length=40)
    beneficiaries: int | None = Field(default=None, ge=0)
    visibility: NeedVisibility = NeedVisibility.public

    @field_validator("categories")
    @classmethod
    def canonical(cls, v: list[str]) -> list[str]:
        return clean_categories(v)


class NeedUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=200)
    description: str | None = Field(default=None, max_length=4000)
    priority: NeedPriority | None = None
    status: NeedStatus | None = None
    quantity: int | None = Field(default=None, gt=0)
    beneficiaries: int | None = Field(default=None, ge=0)
    # Attach a public site plan (null detaches)
    plan_id: UUID | None = None


class NeedOut(BaseModel):
    id: UUID
    event_id: UUID | None
    org: OrgSummary
    # The organisation's public contact address
    contact_email: str
    title: str
    description: str | None
    categories: list[str]
    priority: NeedPriority
    quantity: int | None
    unit: str | None
    beneficiaries: int | None
    latitude: float | None
    longitude: float | None
    place_name: str | None
    status: NeedStatus
    visibility: NeedVisibility
    plan_id: UUID | None = None
    created_at: datetime
    updated_at: datetime
    can_edit: bool = False


class NeedList(BaseModel):
    data: list[NeedOut]
    total: int


# --- offers ---------------------------------------------------------------


class OfferCreate(_Site):
    event_id: UUID | None = None
    title: str = Field(min_length=3, max_length=200)
    description: str | None = Field(default=None, max_length=4000)
    offer_type: OfferType
    categories: list[Category] = Field(min_length=1, max_length=6)
    quantity: int | None = Field(default=None, gt=0)
    unit: str | None = Field(default=None, max_length=40)
    visibility: OfferVisibility = OfferVisibility.public

    @field_validator("categories")
    @classmethod
    def canonical(cls, v: list[str]) -> list[str]:
        return clean_categories(v)


class OfferUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=200)
    description: str | None = Field(default=None, max_length=4000)
    status: OfferStatus | None = None
    quantity: int | None = Field(default=None, gt=0)


class OfferOut(BaseModel):
    """An offer. The creator's identity stays private until a connection is approved."""

    id: UUID
    event_id: UUID | None
    title: str
    description: str | None
    offer_type: OfferType
    categories: list[str]
    quantity: int | None
    unit: str | None
    latitude: float | None
    longitude: float | None
    place_name: str | None
    status: OfferStatus
    visibility: OfferVisibility
    created_at: datetime
    is_mine: bool = False


class OfferList(BaseModel):
    data: list[OfferOut]
    total: int


class MatchOut(BaseModel):
    offer: OfferOut
    score: float
    reasons: list[str]
    distance_km: float | None


class MatchList(BaseModel):
    need_id: UUID
    data: list[MatchOut]


# --- connects ---------------------------------------------------------------


class ConnectCreate(BaseModel):
    need_id: UUID
    offer_id: UUID
    message: str | None = Field(default=None, max_length=1000)


class ConnectOut(BaseModel):
    id: UUID
    need: NeedOut
    offer: OfferOut
    status: ConnectStatus
    message: str | None
    need_approved: bool
    offer_approved: bool
    # Which side(s) the viewer can act for
    my_sides: list[Literal["need", "offer"]]
    # The other side's address, only once both sides approved
    counterpart_email: str | None = None
    created_at: datetime
    approved_at: datetime | None


class ConnectList(BaseModel):
    data: list[ConnectOut]


# --- disclosures ------------------------------------------------------------


class DisclosureCreate(BaseModel):
    org_id: UUID
    title: str = Field(min_length=3, max_length=200)
    body: str = Field(min_length=10, max_length=8000)


class DisclosureOut(BaseModel):
    id: UUID
    event_id: UUID
    org: OrgSummary
    title: str
    body: str
    created_at: datetime


class DisclosureList(BaseModel):
    data: list[DisclosureOut]


class CategoryList(BaseModel):
    data: list[str]


# --- contributions (FR-6.2) --------------------------------------------------


class Badge(BaseModel):
    id: str
    earned: bool
    progress: int
    target: int


class Contributions(BaseModel):
    """What the signed-in user has done, and the badges it earns. Only for themselves."""

    points: int
    counts: dict[str, int]
    badges: list[Badge]
