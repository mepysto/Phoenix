"""Rank offers for a need with a simple, explainable score.

score = 0.5 x category fit + 0.2 x event fit + 0.2 x distance fit + 0.1 x quantity fit

Every part comes with a reason code so the interface can say *why* an offer
is suggested. Matching only recommends: nothing is committed until both
sides approve a connection.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from uuid import UUID

CATEGORIES: tuple[str, ...] = (
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
)

# Beyond this, distance no longer helps the score
DISTANCE_HORIZON_KM = 2000.0


@dataclass(frozen=True)
class NeedInput:
    categories: frozenset[str]
    event_id: UUID | None
    lat: float | None
    lng: float | None
    quantity: int | None
    unit: str | None


@dataclass(frozen=True)
class OfferInput:
    id: UUID
    offer_type: str
    categories: frozenset[str]
    event_id: UUID | None
    lat: float | None
    lng: float | None
    quantity: int | None
    unit: str | None


@dataclass(frozen=True)
class Match:
    offer_id: UUID
    score: float
    reasons: tuple[str, ...]
    distance_km: float | None


def clean_categories(values: list[str] | None) -> list[str]:
    """Known categories only, de-duplicated, in canonical order."""
    wanted = {v.strip().lower() for v in values or []}
    return [c for c in CATEGORIES if c in wanted]


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 6371.0 * 2 * math.asin(math.sqrt(min(1.0, a)))


def score_offer(need: NeedInput, offer: OfferInput) -> Match | None:
    """None when the offer cannot help with this need at all."""
    reasons: list[str] = []

    overlap = need.categories & offer.categories
    if need.categories and overlap:
        category = len(overlap) / len(need.categories)
        reasons.append("category_match")
    elif offer.offer_type == "funding":
        # Money can buy most things, but a direct match is better
        category = 0.5
        reasons.append("funding_any")
    else:
        return None

    if offer.event_id is not None and offer.event_id == need.event_id:
        event = 1.0
        reasons.append("same_event")
    elif offer.event_id is None:
        event = 0.5
        reasons.append("any_event")
    else:
        event = 0.0

    distance_km: float | None = None
    if None not in (need.lat, need.lng, offer.lat, offer.lng):
        distance_km = haversine_km(need.lat, need.lng, offer.lat, offer.lng)  # type: ignore[arg-type]
        distance = max(0.0, 1 - distance_km / DISTANCE_HORIZON_KM)
        if distance > 0.75:
            reasons.append("nearby")
    else:
        distance = 0.5

    quantity = 0.0
    if (
        need.quantity
        and offer.quantity
        and need.unit
        and offer.unit
        and need.unit.strip().lower() == offer.unit.strip().lower()
    ):
        quantity = min(1.0, offer.quantity / need.quantity)
        reasons.append("covers_all" if quantity >= 1 else "covers_part")

    score = 0.5 * category + 0.2 * event + 0.2 * distance + 0.1 * quantity
    return Match(
        offer_id=offer.id,
        score=round(score, 3),
        reasons=tuple(reasons),
        distance_km=None if distance_km is None else round(distance_km, 1),
    )


def rank_offers(need: NeedInput, offers: list[OfferInput], limit: int = 20) -> list[Match]:
    matches = [m for o in offers if (m := score_offer(need, o)) is not None]
    matches.sort(key=lambda m: (-m.score, m.distance_km if m.distance_km is not None else math.inf))
    return matches[:limit]
