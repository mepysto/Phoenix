"""Relief site plans: save, version, fork."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.deps_auth import signed_in_viewer, viewer
from src.db.database import get_db
from src.schemas import plan as s
from src.services.community.service import Viewer
from src.services.plan_service import PlanService

router = APIRouter()


def get_plan_service(session: AsyncSession = Depends(get_db)) -> PlanService:
    return PlanService(session)


Service = Annotated[PlanService, Depends(get_plan_service)]
AnyViewer = Annotated[Viewer, Depends(viewer)]
SignedIn = Annotated[Viewer, Depends(signed_in_viewer)]


@router.get("", response_model=s.PlanList)
async def list_plans(v: AnyViewer, service: Service, event_id: UUID | None = None, mine: bool = False) -> s.PlanList:
    return await service.list(v, event_id, mine and v.user is not None)


@router.post("", response_model=s.PlanOut, status_code=201)
async def create_plan(body: s.PlanCreate, v: SignedIn, service: Service) -> s.PlanOut:
    return await service.create(v, body)


@router.get("/{plan_id}", response_model=s.PlanOut)
async def get_plan(
    plan_id: UUID, v: AnyViewer, service: Service, version: int | None = Query(default=None, ge=1)
) -> s.PlanOut:
    return await service.get(v, plan_id, version)


@router.patch("/{plan_id}", response_model=s.PlanOut)
async def update_plan(plan_id: UUID, body: s.PlanUpdate, v: SignedIn, service: Service) -> s.PlanOut:
    return await service.update(v, plan_id, body)


@router.post("/{plan_id}/versions", response_model=s.PlanOut, status_code=201)
async def save_version(plan_id: UUID, body: s.PlanContent, v: SignedIn, service: Service) -> s.PlanOut:
    """Save the current layout as the plan's next version (author only)."""
    return await service.add_version(v, plan_id, body)


@router.post("/{plan_id}/fork", response_model=s.PlanOut, status_code=201)
async def fork_plan(plan_id: UUID, body: s.PlanFork, v: SignedIn, service: Service) -> s.PlanOut:
    """Copy a version into a new plan you own, to propose changes."""
    return await service.fork(v, plan_id, body)
