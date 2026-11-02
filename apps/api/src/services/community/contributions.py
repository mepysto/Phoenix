"""Contributions and badges (PRD FR-6.2), derived on read.

Counts come straight from what a person did — nothing is stored, so there
is no score to drift or game separately from the work itself. Only the
person sees their own; Phoenix has no public profiles.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from src.models.community import Connect, ConnectStatus, Disclosure, Need, Offer
from src.models.plan import PlanVisibility, SitePlan
from src.schemas.community import Badge, Contributions

# Points per unit of each contribution: connections that got help moving
# count most, then shared plans and public reporting.
POINTS = {
    "offers": 1,
    "needs": 1,
    "connections": 5,
    "plans_public": 3,
    "forks_received": 2,
    "disclosures": 3,
}

# (badge id, count it measures, target)
BADGES: tuple[tuple[str, str, int], ...] = (
    ("first_offer", "offers", 1),
    ("voice_of_need", "needs", 1),
    ("connector", "connections", 1),
    ("steady_connector", "connections", 5),
    ("planner", "plans_public", 1),
    ("remixed", "forks_received", 3),
    ("reporter", "disclosures", 1),
)


def score(counts: dict[str, int]) -> Contributions:
    points = sum(POINTS[k] * counts.get(k, 0) for k in POINTS)
    badges = [
        Badge(id=bid, earned=counts.get(key, 0) >= target, progress=min(counts.get(key, 0), target), target=target)
        for bid, key, target in BADGES
    ]
    return Contributions(points=points, counts={k: counts.get(k, 0) for k in POINTS}, badges=badges)


async def contributions_for(session: AsyncSession, user_id: UUID) -> Contributions:
    async def count(stmt) -> int:
        return int(await session.scalar(stmt) or 0)

    fork = aliased(SitePlan)
    counts = {
        "offers": await count(select(func.count()).select_from(Offer).where(Offer.created_by_user_id == user_id)),
        "needs": await count(select(func.count()).select_from(Need).where(Need.created_by_user_id == user_id)),
        # Connections this person approved on either side, once both agreed
        "connections": await count(
            select(func.count())
            .select_from(Connect)
            .where(
                Connect.status == ConnectStatus.approved,
                or_(Connect.need_approved_by_user_id == user_id, Connect.offer_approved_by_user_id == user_id),
            )
        ),
        "plans_public": await count(
            select(func.count())
            .select_from(SitePlan)
            .where(SitePlan.created_by_user_id == user_id, SitePlan.visibility == PlanVisibility.public)
        ),
        # Forks of this person's plans made by other people
        "forks_received": await count(
            select(func.count())
            .select_from(fork)
            .join(SitePlan, and_(fork.forked_from_id == SitePlan.id))
            .where(SitePlan.created_by_user_id == user_id, fork.created_by_user_id != user_id)
        ),
        "disclosures": await count(
            select(func.count()).select_from(Disclosure).where(Disclosure.created_by_user_id == user_id)
        ),
    }
    return score(counts)
