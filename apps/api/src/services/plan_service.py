"""Saving, versioning and forking relief site plans.

Anyone can read public plans. Signed-in users create plans and fork any
plan they can read; only the author adds versions or changes a plan.
Versions are immutable.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.event import Event
from src.models.plan import PlanVisibility, SitePlan, SitePlanVersion
from src.schemas import plan as s
from src.services.community.service import Forbidden, NotFound, Viewer

LIST_LIMIT = 100


class PlanService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _visible(self, viewer: Viewer):
        q = select(SitePlan)
        if not viewer.admin:
            cond = SitePlan.visibility == PlanVisibility.public
            if viewer.id is not None:
                cond = or_(cond, SitePlan.created_by_user_id == viewer.id)
            q = q.where(cond)
        return q

    async def _get(self, viewer: Viewer, plan_id: UUID) -> SitePlan:
        plan = await self.session.scalar(
            self._visible(viewer).where(SitePlan.id == plan_id).options(selectinload(SitePlan.versions))
        )
        if plan is None:
            raise NotFound("Plan not found")
        return plan

    def _summary(self, plan: SitePlan, latest: SitePlanVersion, viewer: Viewer) -> dict:
        return dict(
            id=plan.id,
            title=plan.title,
            event_id=plan.event_id,
            visibility=plan.visibility,
            latest_version=plan.latest_version,
            population=latest.population,
            item_count=len(latest.items),
            forked_from_id=plan.forked_from_id,
            is_mine=viewer.id is not None and plan.created_by_user_id == viewer.id,
            updated_at=plan.updated_at,
        )

    def _out(self, plan: SitePlan, viewer: Viewer, version: int | None = None) -> s.PlanOut:
        by_number = {v.number: v for v in plan.versions}
        latest = by_number[plan.latest_version]
        chosen = by_number.get(version or plan.latest_version)
        if chosen is None:
            raise NotFound("Version not found")
        # Population and item count describe the version being returned
        summary = {**self._summary(plan, latest, viewer), "population": chosen.population, "item_count": len(chosen.items)}
        return s.PlanOut(
            **summary,
            forked_from_version=plan.forked_from_version,
            version=chosen.number,
            items=[tuple(i) for i in chosen.items],
            note=chosen.note,
            versions=[
                s.PlanVersionMeta(
                    number=v.number,
                    population=v.population,
                    item_count=len(v.items),
                    note=v.note,
                    created_at=v.created_at,
                )
                for v in sorted(plan.versions, key=lambda v: v.number, reverse=True)
            ],
            created_at=plan.created_at,
        )

    async def list(self, viewer: Viewer, event_id: UUID | None, mine: bool) -> s.PlanList:
        q = self._visible(viewer).options(selectinload(SitePlan.versions))
        if event_id:
            q = q.where(SitePlan.event_id == event_id)
        if mine:
            q = q.where(SitePlan.created_by_user_id == viewer.id)
        plans = (await self.session.scalars(q.order_by(SitePlan.updated_at.desc()).limit(LIST_LIMIT))).all()
        out = []
        for p in plans:
            latest = next(v for v in p.versions if v.number == p.latest_version)
            out.append(s.PlanSummary(**self._summary(p, latest, viewer)))
        return s.PlanList(data=out)

    async def get(self, viewer: Viewer, plan_id: UUID, version: int | None) -> s.PlanOut:
        return self._out(await self._get(viewer, plan_id), viewer, version)

    async def create(self, viewer: Viewer, data: s.PlanCreate) -> s.PlanOut:
        assert viewer.user is not None
        if data.event_id is not None and await self.session.get(Event, data.event_id) is None:
            raise NotFound("Event not found")
        plan = SitePlan(
            title=data.title.strip(),
            event_id=data.event_id,
            created_by_user_id=viewer.user.id,
            visibility=data.visibility,
            latest_version=1,
        )
        self.session.add(plan)
        await self.session.flush()
        self.session.add(self._version(plan.id, 1, data, viewer))
        await self.session.flush()
        return await self.get(viewer, plan.id, None)

    def _version(self, plan_id: UUID, number: int, data: s.PlanContent, viewer: Viewer) -> SitePlanVersion:
        assert viewer.user is not None
        return SitePlanVersion(
            plan_id=plan_id,
            number=number,
            population=data.population,
            items=[list(i) for i in data.items],
            note=data.note,
            created_by_user_id=viewer.user.id,
        )

    def _require_owner(self, viewer: Viewer, plan: SitePlan) -> None:
        if not (viewer.admin or plan.created_by_user_id == viewer.id):
            raise Forbidden("Only the plan's author can change it. Fork it to propose changes.")

    async def add_version(self, viewer: Viewer, plan_id: UUID, data: s.PlanContent) -> s.PlanOut:
        plan = await self._get(viewer, plan_id)
        self._require_owner(viewer, plan)
        # Lock the row so two saves cannot take the same number
        locked = await self.session.scalar(select(SitePlan).where(SitePlan.id == plan.id).with_for_update())
        assert locked is not None
        number = locked.latest_version + 1
        self.session.add(self._version(plan.id, number, data, viewer))
        locked.latest_version = number
        await self.session.flush()
        self.session.expire(plan)
        return await self.get(viewer, plan_id, None)

    async def update(self, viewer: Viewer, plan_id: UUID, data: s.PlanUpdate) -> s.PlanOut:
        plan = await self._get(viewer, plan_id)
        self._require_owner(viewer, plan)
        if data.title is not None:
            plan.title = data.title.strip()
        if data.visibility is not None:
            plan.visibility = data.visibility
        await self.session.flush()
        return self._out(plan, viewer)

    async def fork(self, viewer: Viewer, plan_id: UUID, data: s.PlanFork) -> s.PlanOut:
        assert viewer.user is not None
        source = await self._get(viewer, plan_id)
        number = data.version or source.latest_version
        v = next((x for x in source.versions if x.number == number), None)
        if v is None:
            raise NotFound("Version not found")
        count = await self.session.scalar(
            select(func.count()).select_from(SitePlan).where(SitePlan.forked_from_id == source.id)
        )
        plan = SitePlan(
            title=data.title or f"{source.title} (fork {(count or 0) + 1})"[:200],
            event_id=source.event_id,
            created_by_user_id=viewer.user.id,
            forked_from_id=source.id,
            forked_from_version=number,
            visibility=PlanVisibility.public,
            latest_version=1,
        )
        self.session.add(plan)
        await self.session.flush()
        self.session.add(
            SitePlanVersion(
                plan_id=plan.id,
                number=1,
                population=v.population,
                items=v.items,
                note=f"Forked from version {number}",
                created_by_user_id=viewer.user.id,
            )
        )
        await self.session.flush()
        return await self.get(viewer, plan.id, None)

    async def is_public(self, plan_id: UUID) -> bool:
        plan = await self.session.get(SitePlan, plan_id)
        return plan is not None and plan.visibility == PlanVisibility.public
