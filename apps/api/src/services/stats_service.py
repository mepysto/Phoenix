"""Headline figures for the public overview dashboard.

Everything is aggregated in SQL, so the numbers stay right however many
events there are (list endpoints cap at 200 rows). Only public data is
counted: canonical events, public needs of approved organisations, public
offers, and approved connections as a bare count.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.community import (
    Connect,
    ConnectStatus,
    Need,
    NeedStatus,
    NeedVisibility,
    Offer,
    OfferStatus,
    OfferVisibility,
    Org,
    OrgStatus,
)
from src.models.event import Event, SeverityLevel

WEEKS = 12
TOP_N = 8
SEVERITY_ORDER = [s.value for s in (SeverityLevel.low, SeverityLevel.medium, SeverityLevel.high, SeverityLevel.critical)]


class TypeCount(BaseModel):
    type: str
    events: int
    affected: int


class SeverityCount(BaseModel):
    severity: str
    events: int


class WeekCount(BaseModel):
    week_start: date
    events: int


class AffectedEvent(BaseModel):
    id: str
    title: str
    type: str
    severity: str
    country_code: str | None
    region: str | None
    affected: int


class CategoryCount(BaseModel):
    category: str
    open: int
    closed: int


class OverviewStats(BaseModel):
    generated_at: datetime
    active_events: int
    critical_active: int
    affected_active: int
    # Active events that carry a people-affected figure; 0 means "not yet counted", not "nobody"
    affected_estimated: int
    countries_active: int
    new_this_week: int
    new_week_before: int
    by_type: list[TypeCount]
    by_severity: list[SeverityCount]
    weekly_onsets: list[WeekCount]
    top_affected: list[AffectedEvent]
    needs_open: int
    offers_open: int
    connections_made: int
    needs_by_category: list[CategoryCount]


def _week_start(d: datetime) -> date:
    day = d.astimezone(UTC).date()
    return day - timedelta(days=day.weekday())  # Monday, as date_trunc('week')


class StatsService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def overview(self, now: datetime | None = None) -> OverviewStats:
        now = now or datetime.now(UTC)
        canonical = Event.is_canonical.is_(True)
        active = (canonical, Event.is_active.is_(True))
        affected = func.coalesce(func.sum(Event.affected_population), 0)

        totals = (
            await self.session.execute(
                select(
                    func.count(),
                    func.count().filter(Event.severity == SeverityLevel.critical),
                    affected,
                    func.count(func.distinct(Event.country_code)),
                    func.count().filter(Event.affected_population > 0),
                ).where(*active)
            )
        ).one()

        by_type = (
            await self.session.execute(
                select(Event.type, func.count(), affected).where(*active).group_by(Event.type)
            )
        ).all()
        by_severity = dict(
            (await self.session.execute(select(Event.severity, func.count()).where(*active).group_by(Event.severity))).all()
        )

        this_week = _week_start(now)
        first_week = this_week - timedelta(weeks=WEEKS - 1)
        since = datetime.combine(first_week, datetime.min.time(), tzinfo=UTC)
        bucket = func.date_trunc("week", func.timezone("UTC", Event.start_date))
        weekly = dict(
            (
                (row[0].date(), row[1])
                for row in (
                    await self.session.execute(
                        select(bucket, func.count()).where(canonical, Event.start_date >= since).group_by(bucket)
                    )
                ).all()
            )
        )

        recent = (
            await self.session.execute(
                select(
                    func.count().filter(Event.start_date >= now - timedelta(days=7)),
                    func.count().filter(
                        Event.start_date < now - timedelta(days=7),
                        Event.start_date >= now - timedelta(days=14),
                    ),
                ).where(canonical, Event.start_date <= now)
            )
        ).one()

        top = (
            await self.session.execute(
                select(Event)
                .where(*active, Event.affected_population > 0)
                .order_by(Event.affected_population.desc(), Event.start_date.desc())
                .limit(TOP_N)
            )
        ).scalars()

        public_needs = (
            select(Need.status, func.jsonb_array_elements_text(Need.categories).label("category"))
            .join(Org, Org.id == Need.org_id)
            .where(Org.status == OrgStatus.approved, Need.visibility == NeedVisibility.public)
            .subquery()
        )
        categories = (
            await self.session.execute(
                select(
                    public_needs.c.category,
                    func.count().filter(public_needs.c.status == NeedStatus.open),
                    func.count().filter(public_needs.c.status == NeedStatus.closed),
                ).group_by(public_needs.c.category)
            )
        ).all()
        needs_open = await self.session.scalar(
            select(func.count())
            .select_from(Need)
            .join(Org, Org.id == Need.org_id)
            .where(
                Org.status == OrgStatus.approved,
                Need.visibility == NeedVisibility.public,
                Need.status == NeedStatus.open,
            )
        )
        offers_open = await self.session.scalar(
            select(func.count()).where(Offer.visibility == OfferVisibility.public, Offer.status == OfferStatus.open)
        )
        connections = await self.session.scalar(
            select(func.count()).where(Connect.status == ConnectStatus.approved)
        )

        return OverviewStats(
            generated_at=now,
            active_events=totals[0],
            critical_active=totals[1],
            affected_active=int(totals[2]),
            affected_estimated=totals[4],
            countries_active=totals[3],
            new_this_week=recent[0],
            new_week_before=recent[1],
            by_type=sorted(
                (TypeCount(type=t.value, events=n, affected=int(a)) for t, n, a in by_type),
                key=lambda x: (-x.events, -x.affected, x.type),
            ),
            by_severity=[
                SeverityCount(severity=s, events=by_severity.get(SeverityLevel(s), 0)) for s in SEVERITY_ORDER
            ],
            weekly_onsets=[
                WeekCount(week_start=w, events=weekly.get(w, 0))
                for w in (first_week + timedelta(weeks=i) for i in range(WEEKS))
            ],
            top_affected=[
                AffectedEvent(
                    id=str(e.id),
                    title=e.title,
                    type=e.type.value,
                    severity=e.severity.value,
                    country_code=e.country_code,
                    region=e.region,
                    affected=e.affected_population or 0,
                )
                for e in top
            ],
            needs_open=needs_open or 0,
            offers_open=offers_open or 0,
            connections_made=connections or 0,
            needs_by_category=sorted(
                (CategoryCount(category=c, open=o, closed=cl) for c, o, cl in categories),
                key=lambda x: (-x.open, -x.closed, x.category),
            ),
        )
