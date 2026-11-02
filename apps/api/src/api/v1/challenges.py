"""Design challenges (recovery design hackathons)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.deps_auth import signed_in_viewer, viewer
from src.db.database import get_db
from src.services import challenge_service as cs
from src.services.community.service import Viewer

router = APIRouter()


def get_service(session: AsyncSession = Depends(get_db)) -> cs.ChallengeService:
    return cs.ChallengeService(session)


Service = Annotated[cs.ChallengeService, Depends(get_service)]
AnyViewer = Annotated[Viewer, Depends(viewer)]
SignedIn = Annotated[Viewer, Depends(signed_in_viewer)]


@router.get("", response_model=cs.ChallengeList)
async def list_challenges(service: Service, event_id: UUID | None = None) -> cs.ChallengeList:
    return await service.list(event_id)


@router.post("", response_model=cs.ChallengeOut, status_code=201)
async def create_challenge(body: cs.ChallengeCreate, v: SignedIn, service: Service) -> cs.ChallengeOut:
    return await service.create(v, body)


@router.get("/{challenge_id}", response_model=cs.ChallengeOut)
async def get_challenge(challenge_id: UUID, v: AnyViewer, service: Service) -> cs.ChallengeOut:
    return await service.get(v, challenge_id)


@router.post("/{challenge_id}/entries", response_model=cs.ChallengeOut, status_code=201)
async def submit_entry(challenge_id: UUID, body: cs.EntrySubmit, v: SignedIn, service: Service) -> cs.ChallengeOut:
    """Enter one of your public site plans."""
    return await service.submit(v, challenge_id, body)


@router.post("/entries/{entry_id}/vote", response_model=cs.ChallengeOut)
async def vote(entry_id: UUID, v: SignedIn, service: Service) -> cs.ChallengeOut:
    return await service.vote(v, entry_id, True)


@router.post("/entries/{entry_id}/unvote", response_model=cs.ChallengeOut)
async def unvote(entry_id: UUID, v: SignedIn, service: Service) -> cs.ChallengeOut:
    return await service.vote(v, entry_id, False)


@router.post("/{challenge_id}/select", response_model=cs.ChallengeOut)
async def select_entry(challenge_id: UUID, body: cs.EntrySelect, v: SignedIn, service: Service) -> cs.ChallengeOut:
    """Host organisation: pick the entry to take forward (null clears it)."""
    return await service.select(v, challenge_id, body)
