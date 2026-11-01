"""How far to trust an event, and where it is in its lifecycle.

Both values are derived on read from what the event row already holds (its
sources, dates and activity flag), so they need no schema change and are
always consistent with the data behind them.

Confidence (0.1-1.0) rises with the number of independent sources that report
the event and falls while an active event goes unconfirmed:

    base(best source tier) + 0.15 x (independent sources - 1) - staleness

Lifecycle stages, in order:

    detected -> verified -> responding -> recovering -> closed

The stage is a reading aid, not an operational status: Phoenix does not know
what responders are doing on the ground, only how long ago the event began and
whether its sources still report it as active.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Literal

from pydantic import BaseModel

Lifecycle = Literal["detected", "verified", "responding", "recovering", "closed"]

LIFECYCLE_STAGES: tuple[Lifecycle, ...] = (
    "detected",
    "verified",
    "responding",
    "recovering",
    "closed",
)

# Authoritative agencies that issue the alert themselves score higher than
# aggregators of other agencies' reports.
SOURCE_TIERS: dict[str, float] = {
    "usgs": 0.6,
    "gdacs": 0.6,
    "copernicus": 0.6,
    "eonet": 0.5,
}
DEFAULT_TIER = 0.4

PER_EXTRA_SOURCE = 0.15
STALE_AFTER = timedelta(hours=24)
STALE_PENALTY_PER_DAY = 0.05
MAX_STALE_PENALTY = 0.2

# Without a confirming second source, an event is "detected" for this long
VERIFY_WINDOW = timedelta(hours=6)
# Active events older than this are treated as being in recovery
RESPONSE_WINDOW = timedelta(days=14)


class EventTrust(BaseModel):
    confidence: float
    source_count: int
    lifecycle: Lifecycle
    # Machine-readable reasons; the UI translates them
    reasons: list[str]


def _tier(name: str) -> float:
    return SOURCE_TIERS.get(name.strip().lower(), DEFAULT_TIER)


def compute_trust(
    *,
    source_names: list[str],
    is_active: bool,
    start_date: datetime,
    end_date: datetime | None,
    updated_at: datetime | None,
    now: datetime | None = None,
) -> EventTrust:
    """Confidence and lifecycle stage for one event."""
    now = now or datetime.now(UTC)
    distinct = sorted({n.strip().lower() for n in source_names if n and n.strip()})
    count = len(distinct)
    reasons: list[str] = []

    if count == 0:
        confidence = 0.3
        reasons.append("no_source")
    else:
        best = max(_tier(n) for n in distinct)
        confidence = best + PER_EXTRA_SOURCE * (count - 1)
        if best >= 0.6:
            reasons.append("authoritative_source")
        if count > 1:
            reasons.append("multi_source")

    last_seen = updated_at or start_date
    if is_active and last_seen and now - last_seen > STALE_AFTER:
        days = (now - last_seen - STALE_AFTER) / timedelta(days=1)
        confidence -= min(MAX_STALE_PENALTY, STALE_PENALTY_PER_DAY * (1 + int(days)))
        reasons.append("stale")

    confidence = round(min(1.0, max(0.1, confidence)), 2)

    age = now - start_date
    ended = end_date is not None and end_date <= now
    if not is_active or ended:
        lifecycle: Lifecycle = "closed"
    elif count <= 1 and confidence < 0.6 and age < VERIFY_WINDOW:
        lifecycle = "detected"
    elif age < timedelta(hours=24):
        lifecycle = "verified"
    elif age < RESPONSE_WINDOW:
        lifecycle = "responding"
    else:
        lifecycle = "recovering"

    return EventTrust(
        confidence=confidence,
        source_count=count,
        lifecycle=lifecycle,
        reasons=reasons,
    )
