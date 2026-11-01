"""Organisations, needs, offers, matching, connections and disclosures."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from src.api.v1.deps_auth import get_community_service, signed_in_viewer, viewer
from src.models.community import NeedStatus, OfferStatus, OrgStatus
from src.schemas import community as s
from src.services.community.matching import CATEGORIES
from src.services.community.service import CommunityService, Viewer

router = APIRouter()

Service = Annotated[CommunityService, Depends(get_community_service)]
AnyViewer = Annotated[Viewer, Depends(viewer)]
SignedIn = Annotated[Viewer, Depends(signed_in_viewer)]


@router.get("/categories", response_model=s.CategoryList)
async def categories() -> s.CategoryList:
    return s.CategoryList(data=list(CATEGORIES))


# --- orgs -------------------------------------------------------------------


@router.post("/orgs", response_model=s.OrgSummary, status_code=201)
async def apply_org(body: s.OrgCreate, v: SignedIn, service: Service) -> s.OrgSummary:
    """Apply for an organisation. It can post needs once a platform admin approves it."""
    return await service.apply_org(v, body)


@router.post("/orgs/{org_id}/members", response_model=s.Membership, status_code=201)
async def add_member(org_id: UUID, body: s.MemberAdd, v: SignedIn, service: Service) -> s.Membership:
    return await service.add_member(v, org_id, body)


@router.get("/admin/orgs", response_model=list[s.OrgAdminView])
async def orgs_for_review(v: SignedIn, service: Service, status: OrgStatus | None = None) -> list[s.OrgAdminView]:
    return await service.list_orgs_for_review(v, status)


@router.post("/admin/orgs/{org_id}/approve", response_model=s.OrgSummary)
async def approve_org(org_id: UUID, v: SignedIn, service: Service) -> s.OrgSummary:
    return await service.decide_org(v, org_id, True, None)


@router.post("/admin/orgs/{org_id}/reject", response_model=s.OrgSummary)
async def reject_org(org_id: UUID, body: s.OrgDecision, v: SignedIn, service: Service) -> s.OrgSummary:
    return await service.decide_org(v, org_id, False, body.reason)


# --- needs --------------------------------------------------------------------


@router.get("/needs", response_model=s.NeedList)
async def list_needs(
    v: AnyViewer,
    service: Service,
    event_id: UUID | None = None,
    org_id: UUID | None = None,
    category: s.Category | None = None,
    status: NeedStatus | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> s.NeedList:
    return await service.list_needs(
        v, event_id=event_id, org_id=org_id, category=category, status=status, limit=limit, offset=offset
    )


@router.post("/needs", response_model=s.NeedOut, status_code=201)
async def create_need(body: s.NeedCreate, v: SignedIn, service: Service) -> s.NeedOut:
    return await service.create_need(v, body)


@router.get("/needs/{need_id}", response_model=s.NeedOut)
async def get_need(need_id: UUID, v: AnyViewer, service: Service) -> s.NeedOut:
    return await service.get_need(v, need_id)


@router.patch("/needs/{need_id}", response_model=s.NeedOut)
async def update_need(need_id: UUID, body: s.NeedUpdate, v: SignedIn, service: Service) -> s.NeedOut:
    return await service.update_need(v, need_id, body)


@router.get("/needs/{need_id}/matches", response_model=s.MatchList)
async def need_matches(
    need_id: UUID, v: AnyViewer, service: Service, limit: int = Query(20, ge=1, le=50)
) -> s.MatchList:
    """Open offers ranked for this need, with the reasons for each score."""
    return await service.matches(v, need_id, limit)


# --- offers -------------------------------------------------------------------


@router.get("/offers", response_model=s.OfferList)
async def list_offers(
    v: AnyViewer,
    service: Service,
    event_id: UUID | None = None,
    category: s.Category | None = None,
    mine: bool = False,
    status: OfferStatus | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> s.OfferList:
    return await service.list_offers(
        v, event_id=event_id, category=category, mine=mine and v.user is not None,
        status=status, limit=limit, offset=offset,
    )


@router.post("/offers", response_model=s.OfferOut, status_code=201)
async def create_offer(body: s.OfferCreate, v: SignedIn, service: Service) -> s.OfferOut:
    return await service.create_offer(v, body)


@router.patch("/offers/{offer_id}", response_model=s.OfferOut)
async def update_offer(offer_id: UUID, body: s.OfferUpdate, v: SignedIn, service: Service) -> s.OfferOut:
    return await service.update_offer(v, offer_id, body)


# --- connects -----------------------------------------------------------------


@router.get("/connects", response_model=s.ConnectList)
async def my_connects(v: SignedIn, service: Service) -> s.ConnectList:
    return await service.my_connects(v)


@router.post("/connects", response_model=s.ConnectOut, status_code=201)
async def create_connect(body: s.ConnectCreate, v: SignedIn, service: Service) -> s.ConnectOut:
    """Propose a connection. The proposer's side counts as approved."""
    return await service.create_connect(v, body)


@router.post("/connects/{connect_id}/approve", response_model=s.ConnectOut)
async def approve_connect(connect_id: UUID, v: SignedIn, service: Service) -> s.ConnectOut:
    return await service.approve_connect(v, connect_id)


@router.post("/connects/{connect_id}/decline", response_model=s.ConnectOut)
async def decline_connect(connect_id: UUID, v: SignedIn, service: Service) -> s.ConnectOut:
    return await service.decline_connect(v, connect_id)


# --- disclosures --------------------------------------------------------------


@router.get("/events/{event_id}/disclosures", response_model=s.DisclosureList)
async def list_disclosures(event_id: UUID, service: Service) -> s.DisclosureList:
    return await service.list_disclosures(event_id)


@router.post("/events/{event_id}/disclosures", response_model=s.DisclosureOut, status_code=201)
async def create_disclosure(
    event_id: UUID, body: s.DisclosureCreate, v: SignedIn, service: Service
) -> s.DisclosureOut:
    return await service.create_disclosure(v, event_id, body)
