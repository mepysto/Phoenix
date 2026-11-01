"""Match new events to push subscribers' areas and send the alerts.

Runs as a scheduler job. Each (subscription, event) pair is delivered at
most once (push_deliveries). Only events created after the subscription
alert, at most a few per subscription per run, most severe first.
Subscriptions the push service reports as gone (404/410) are deleted.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Protocol
from urllib.parse import urlsplit

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.event import Event
from src.models.push import PushDelivery, PushSubscription
from src.services.community.matching import haversine_km
from src.services.push.webpush import VapidKeys, push_request

logger = logging.getLogger(__name__)

# The server only ever POSTs to these push services (no SSRF via "endpoints")
PUSH_HOST_SUFFIXES = (
    "fcm.googleapis.com",
    "push.services.mozilla.com",
    "push.apple.com",
    "notify.windows.com",
)
SEVERITY_RANK = {"low": 0, "medium": 1, "high": 2, "critical": 3}
WINDOW = timedelta(hours=1)
PER_SUBSCRIPTION_PER_RUN = 3
MAX_FAILURES = 5


def is_push_endpoint(url: str) -> bool:
    parts = urlsplit(url)
    host = (parts.hostname or "").lower()
    return (
        parts.scheme == "https"
        and parts.username is None
        and parts.port in (None, 443)
        and any(host == s or host.endswith("." + s) for s in PUSH_HOST_SUFFIXES)
    )


def matching_area(event: Event, areas: list[dict]) -> tuple[str, float] | None:
    """(area name, distance km) of the nearest area the event falls in."""
    if event.latitude is None or event.longitude is None:
        return None
    rank = SEVERITY_RANK.get(event.severity.value, 0)
    best: tuple[str, float] | None = None
    for a in areas:
        if rank < SEVERITY_RANK.get(a.get("min_severity", "high"), 2):
            continue
        d = haversine_km(event.latitude, event.longitude, a["lat"], a["lng"])
        if d <= a["radius_km"] and (best is None or d < best[1]):
            best = (str(a.get("name", "")), d)
    return best


class Poster(Protocol):
    async def post(self, url: str, *, headers: dict[str, str], content: bytes) -> object: ...


async def dispatch(
    session: AsyncSession,
    keys: VapidKeys,
    subject: str,
    client: Poster,
    now: datetime | None = None,
) -> dict[str, int]:
    now = now or datetime.now(UTC)
    events = (
        await session.scalars(
            select(Event)
            .where(Event.created_at > now - WINDOW, Event.is_active.is_(True), Event.is_canonical.is_(True))
            .order_by(Event.created_at.desc())
            .limit(500)
        )
    ).all()
    if not events:
        return {"events": 0, "sent": 0, "removed": 0}
    subs = (await session.scalars(select(PushSubscription).limit(20_000))).all()
    delivered = {
        (s, e)
        for s, e in (
            await session.execute(
                select(PushDelivery.subscription_id, PushDelivery.event_id).where(
                    PushDelivery.event_id.in_([e.id for e in events])
                )
            )
        ).all()
    }
    by_severity = sorted(events, key=lambda e: -SEVERITY_RANK.get(e.severity.value, 0))
    sent = removed = 0
    for sub in subs:
        batch = 0
        for event in by_severity:
            if batch >= PER_SUBSCRIPTION_PER_RUN:
                break
            if event.created_at <= sub.created_at or (sub.id, event.id) in delivered:
                continue
            hit = matching_area(event, sub.areas)
            if hit is None:
                continue
            name, km = hit
            headers, body = push_request(
                sub.endpoint,
                sub.p256dh,
                sub.auth,
                {"title": event.title, "body": f"{name} · {round(km)} km", "url": f"/events/{event.id}", "tag": str(event.id)},
                keys,
                subject,
            )
            try:
                response = await client.post(sub.endpoint, headers=headers, content=body)
                status = getattr(response, "status_code", 0)
            except Exception:
                logger.warning("Push to %s failed", urlsplit(sub.endpoint).hostname)
                status = 0
            if status in (404, 410):
                await session.delete(sub)
                removed += 1
                break
            if 200 <= status < 300:
                session.add(PushDelivery(subscription_id=sub.id, event_id=event.id))
                sub.failures = 0
                sent += 1
                batch += 1
            else:
                sub.failures += 1
                if sub.failures >= MAX_FAILURES:
                    await session.delete(sub)
                    removed += 1
                    break
    # Delivery records only need to outlive the matching window
    await session.execute(delete(PushDelivery).where(PushDelivery.sent_at < now - timedelta(days=2)))
    await session.flush()
    return {"events": len(events), "sent": sent, "removed": removed}
