"""Design challenges: create, submit plans, vote, select an entry.

Rules:
- Members of an approved organisation open challenges for it.
- While a challenge is open, anyone signed in submits one of their own
  public plans; each plan enters a challenge once.
- Signed-in users vote once per entry, never for their own entry, and
  only while the challenge is open.
- The host organisation's members select an entry to take forward, at
  any time; selection is shown to everyone.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.challenge import Challenge, ChallengeEntry, ChallengeVote
from src.models.community import Org, OrgStatus
from src.models.event import Event
from src.models.plan import PlanVisibility, SitePlan
from src.schemas.community import OrgSummary
from src.services.community.service import Conflict, Forbidden, NotFound, Viewer, _org_summary


class ChallengeCreate(BaseModel):
    org_id: UUID
    event_id: UUID | None = None
    title: str = Field(min_length=3, max_length=200)
    brief: str = Field(min_length=10, max_length=4000)
    population: int = Field(gt=0, le=1_000_000)
    closes_at: datetime

    @field_validator("closes_at")
    @classmethod
    def in_future(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            v = v.replace(tzinfo=UTC)
        if v <= datetime.now(UTC):
            raise ValueError("The closing date must be in the future")
        return v


class EntrySubmit(BaseModel):
    plan_id: UUID


class EntrySelect(BaseModel):
    entry_id: UUID | None


class EntryOut(BaseModel):
    id: UUID
    plan_id: UUID
    plan_title: str
    plan_version: int
    population: int
    item_count: int
    votes: int
    voted_by_me: bool
    is_mine: bool
    selected: bool
    created_at: datetime


class ChallengeSummary(BaseModel):
    id: UUID
    org: OrgSummary
    event_id: UUID | None
    title: str
    population: int
    closes_at: datetime
    is_open: bool
    entry_count: int
    has_selection: bool


class ChallengeOut(ChallengeSummary):
    brief: str
    can_manage: bool
    entries: list[EntryOut]


class ChallengeList(BaseModel):
    data: list[ChallengeSummary]


def _is_open(c: Challenge, now: datetime | None = None) -> bool:
    return (now or datetime.now(UTC)) < c.closes_at


class ChallengeService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _get(self, challenge_id: UUID) -> Challenge:
        c = await self.session.scalar(
            select(Challenge)
            .join(Org, Org.id == Challenge.org_id)
            .where(Challenge.id == challenge_id, Org.status == OrgStatus.approved)
        )
        if c is None:
            raise NotFound("Challenge not found")
        return c

    async def _org(self, c: Challenge) -> Org:
        org = await self.session.get(Org, c.org_id)
        assert org is not None
        return org

    async def list(self, event_id: UUID | None) -> ChallengeList:
        counts = (
            select(ChallengeEntry.challenge_id, func.count().label("n"))
            .group_by(ChallengeEntry.challenge_id)
            .subquery()
        )
        q = (
            select(Challenge, Org, func.coalesce(counts.c.n, 0))
            .join(Org, Org.id == Challenge.org_id)
            .outerjoin(counts, counts.c.challenge_id == Challenge.id)
            .where(Org.status == OrgStatus.approved)
            .order_by(Challenge.closes_at.desc())
            .limit(100)
        )
        if event_id:
            q = q.where(Challenge.event_id == event_id)
        now = datetime.now(UTC)
        rows = (await self.session.execute(q)).all()
        return ChallengeList(
            data=[
                ChallengeSummary(
                    id=c.id,
                    org=_org_summary(org),
                    event_id=c.event_id,
                    title=c.title,
                    population=c.population,
                    closes_at=c.closes_at,
                    is_open=_is_open(c, now),
                    entry_count=int(n),
                    has_selection=c.selected_entry_id is not None,
                )
                for c, org, n in rows
            ]
        )

    async def get(self, viewer: Viewer, challenge_id: UUID) -> ChallengeOut:
        c = await self._get(challenge_id)
        org = await self._org(c)
        votes = (
            select(ChallengeVote.entry_id, func.count().label("n")).group_by(ChallengeVote.entry_id).subquery()
        )
        rows = (
            await self.session.execute(
                select(ChallengeEntry, SitePlan, func.coalesce(votes.c.n, 0))
                .join(SitePlan, SitePlan.id == ChallengeEntry.plan_id)
                .outerjoin(votes, votes.c.entry_id == ChallengeEntry.id)
                .where(ChallengeEntry.challenge_id == c.id, SitePlan.visibility == PlanVisibility.public)
                .options(selectinload(SitePlan.versions))
            )
        ).all()
        mine: set[UUID] = set()
        if viewer.id is not None and rows:
            mine = set(
                (
                    await self.session.scalars(
                        select(ChallengeVote.entry_id).where(
                            ChallengeVote.user_id == viewer.id,
                            ChallengeVote.entry_id.in_([e.id for e, _, _ in rows]),
                        )
                    )
                ).all()
            )
        entries = []
        for e, plan, n in rows:
            latest = next(v for v in plan.versions if v.number == plan.latest_version)
            entries.append(
                EntryOut(
                    id=e.id,
                    plan_id=plan.id,
                    plan_title=plan.title,
                    plan_version=plan.latest_version,
                    population=latest.population,
                    item_count=len(latest.items),
                    votes=int(n),
                    voted_by_me=e.id in mine,
                    is_mine=viewer.id is not None and e.submitted_by_user_id == viewer.id,
                    selected=c.selected_entry_id == e.id,
                    created_at=e.created_at,
                )
            )
        # Selected first, then most votes, then earliest
        entries.sort(key=lambda x: (not x.selected, -x.votes, x.created_at))
        return ChallengeOut(
            id=c.id,
            org=_org_summary(org),
            event_id=c.event_id,
            title=c.title,
            population=c.population,
            closes_at=c.closes_at,
            is_open=_is_open(c),
            entry_count=len(entries),
            has_selection=c.selected_entry_id is not None,
            brief=c.brief,
            can_manage=viewer.admin or viewer.member_of_approved(c.org_id),
            entries=entries,
        )

    async def create(self, viewer: Viewer, data: ChallengeCreate) -> ChallengeOut:
        assert viewer.user is not None
        if not viewer.member_of_approved(data.org_id):
            raise Forbidden("Only members of an approved organisation can open a challenge for it")
        if data.event_id is not None and await self.session.get(Event, data.event_id) is None:
            raise NotFound("Event not found")
        c = Challenge(**data.model_dump(), created_by_user_id=viewer.user.id)
        self.session.add(c)
        await self.session.flush()
        return await self.get(viewer, c.id)

    async def submit(self, viewer: Viewer, challenge_id: UUID, data: EntrySubmit) -> ChallengeOut:
        assert viewer.user is not None
        c = await self._get(challenge_id)
        if not _is_open(c):
            raise Conflict("This challenge is closed")
        plan = await self.session.get(SitePlan, data.plan_id)
        if plan is None or plan.created_by_user_id != viewer.user.id:
            raise NotFound("Plan not found among your plans")
        if plan.visibility != PlanVisibility.public:
            raise Conflict("Make the plan public before entering it")
        self.session.add(ChallengeEntry(challenge_id=c.id, plan_id=plan.id, submitted_by_user_id=viewer.user.id))
        try:
            await self.session.flush()
        except IntegrityError as exc:
            raise Conflict("This plan is already entered") from exc
        return await self.get(viewer, c.id)

    async def _entry(self, entry_id: UUID) -> tuple[ChallengeEntry, Challenge]:
        entry = await self.session.get(ChallengeEntry, entry_id)
        if entry is None:
            raise NotFound("Entry not found")
        return entry, await self._get(entry.challenge_id)

    async def vote(self, viewer: Viewer, entry_id: UUID, on: bool) -> ChallengeOut:
        assert viewer.user is not None
        entry, c = await self._entry(entry_id)
        if not _is_open(c):
            raise Conflict("Voting has closed")
        if on:
            if entry.submitted_by_user_id == viewer.user.id:
                raise Conflict("You cannot vote for your own entry")
            exists = await self.session.get(ChallengeVote, (entry.id, viewer.user.id))
            if exists is None:
                self.session.add(ChallengeVote(entry_id=entry.id, user_id=viewer.user.id))
        else:
            await self.session.execute(
                delete(ChallengeVote).where(ChallengeVote.entry_id == entry.id, ChallengeVote.user_id == viewer.user.id)
            )
        await self.session.flush()
        return await self.get(viewer, c.id)

    async def select(self, viewer: Viewer, challenge_id: UUID, data: EntrySelect) -> ChallengeOut:
        c = await self._get(challenge_id)
        if not (viewer.admin or viewer.member_of_approved(c.org_id)):
            raise Forbidden("Only the host organisation can select an entry")
        if data.entry_id is not None:
            entry = await self.session.get(ChallengeEntry, data.entry_id)
            if entry is None or entry.challenge_id != c.id:
                raise NotFound("Entry not found in this challenge")
        c.selected_entry_id = data.entry_id
        await self.session.flush()
        return await self.get(viewer, c.id)
