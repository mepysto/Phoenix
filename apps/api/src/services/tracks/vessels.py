"""Ships near active disasters from AISStream (G-12).

AISStream is a WebSocket firehose that must be consumed server-side and
allows 3 connections per account, so exactly one stream runs per
deployment (in the process that runs the scheduler). It subscribes only to
boxes around active high/critical events, buffers the latest report per
ship and writes them to PostgreSQL every few seconds; the API serves the
map from there.

Use: relief shipments, port congestion or closure, evacuations by sea.
"""

import asyncio
import json
import logging
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.models.event import Event, SeverityLevel
from src.models.vessel import VesselPosition
from src.utils.geo import envelope_filter

logger = logging.getLogger(__name__)

STREAM_URL = "wss://stream.aisstream.io/v0/stream"
FLUSH_SECONDS = 5
RESUBSCRIBE_SECONDS = 600  # follow new/ended events
RETENTION = timedelta(hours=2)
MAX_BACKOFF_SECONDS = 300
MESSAGE_TYPES = ["PositionReport", "StandardClassBPositionReport", "ShipStaticData"]

# AIS "not available" values
NO_HEADING = 511
NO_COURSE = 360
NO_SPEED = 102.3


@dataclass
class VesselUpdate:
    mmsi: int
    latitude: float | None = None
    longitude: float | None = None
    speed_kn: float | None = None
    course_deg: float | None = None
    heading_deg: float | None = None
    name: str | None = None
    ship_type: int | None = None
    at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def merge(self, newer: "VesselUpdate") -> "VesselUpdate":
        """Newer values win; fields the newer report lacks are kept."""
        changes = {k: v for k, v in newer.__dict__.items() if v is not None}
        return replace(self, **changes)


def _num(value: Any, invalid: float | None = None) -> float | None:
    if not isinstance(value, int | float) or isinstance(value, bool):
        return None
    return None if invalid is not None and value >= invalid else float(value)


def parse_message(raw: str | bytes) -> VesselUpdate | None:
    """One AISStream message → an update, or None for anything unusable."""
    try:
        message = json.loads(raw)
    except (ValueError, TypeError):
        return None
    if not isinstance(message, dict):
        return None
    kind = message.get("MessageType")
    body = (message.get("Message") or {}).get(kind) or {}
    meta = message.get("MetaData") or {}
    mmsi = body.get("UserID") or meta.get("MMSI")
    if not isinstance(mmsi, int) or not (100_000_000 <= mmsi <= 999_999_999):
        return None
    name = (meta.get("ShipName") or body.get("Name") or "").strip()[:32] or None

    if kind in ("PositionReport", "StandardClassBPositionReport"):
        lat, lng = _num(body.get("Latitude")), _num(body.get("Longitude"))
        if body.get("Valid") is False or lat is None or lng is None or abs(lat) > 90 or abs(lng) > 180:
            return None
        return VesselUpdate(
            mmsi=mmsi,
            latitude=lat,
            longitude=lng,
            speed_kn=_num(body.get("Sog"), NO_SPEED),
            course_deg=_num(body.get("Cog"), NO_COURSE),
            heading_deg=_num(body.get("TrueHeading"), NO_HEADING),
            name=name,
        )
    if kind == "ShipStaticData":
        ship_type = body.get("Type")
        return VesselUpdate(mmsi=mmsi, name=name, ship_type=ship_type if isinstance(ship_type, int) else None)
    return None


def subscription_boxes(points: Iterable[tuple[float, float]], half_width: float, limit: int) -> list[list[list[float]]]:
    """AISStream bounding boxes ([[lat, lng], [lat, lng]]) around event locations."""
    boxes = []
    for lat, lng in list(points)[:limit]:
        south, north = max(-90.0, lat - half_width), min(90.0, lat + half_width)
        west, east = lng - half_width, lng + half_width
        # AISStream boxes do not wrap: split at the antimeridian
        if west < -180:
            boxes += [[[south, west + 360], [north, 180.0]], [[south, -180.0], [north, east]]]
        elif east > 180:
            boxes += [[[south, west], [north, 180.0]], [[south, -180.0], [north, east - 360]]]
        else:
            boxes.append([[south, west], [north, east]])
    return boxes


async def watched_points(session: AsyncSession, limit: int) -> list[tuple[float, float]]:
    """Locations of active high/critical events, most severe and newest first."""
    rows = await session.execute(
        select(Event.latitude, Event.longitude)
        .where(
            Event.is_active.is_(True),
            Event.is_canonical.is_(True),
            Event.severity.in_([SeverityLevel.critical, SeverityLevel.high]),
            Event.latitude.isnot(None),
            Event.longitude.isnot(None),
        )
        .order_by((Event.severity == SeverityLevel.critical).desc(), Event.start_date.desc())
        .limit(limit)
    )
    return [(lat, lng) for lat, lng in rows.all()]


async def store(session: AsyncSession, updates: Iterable[VesselUpdate], now: datetime) -> int:
    """Upsert positions (static-only reports just name ships we already track); prune old rows."""
    rows = [
        {
            "mmsi": u.mmsi,
            "name": u.name,
            "ship_type": u.ship_type,
            "latitude": u.latitude,
            "longitude": u.longitude,
            "speed_kn": u.speed_kn,
            "course_deg": u.course_deg,
            "heading_deg": u.heading_deg,
            "location": func.ST_SetSRID(func.ST_MakePoint(u.longitude, u.latitude), 4326),
            "updated_at": u.at,
        }
        for u in updates
        if u.latitude is not None and u.longitude is not None
    ]
    written = 0
    if rows:
        stmt = insert(VesselPosition).values(rows)
        keep = lambda column: func.coalesce(stmt.excluded[column], getattr(VesselPosition, column))  # noqa: E731
        stmt = stmt.on_conflict_do_update(
            index_elements=[VesselPosition.mmsi],
            set_={
                "name": keep("name"),
                "ship_type": keep("ship_type"),
                "latitude": stmt.excluded.latitude,
                "longitude": stmt.excluded.longitude,
                "speed_kn": stmt.excluded.speed_kn,
                "course_deg": stmt.excluded.course_deg,
                "heading_deg": stmt.excluded.heading_deg,
                "location": stmt.excluded.location,
                "updated_at": stmt.excluded.updated_at,
            },
        )
        written = (await session.execute(stmt)).rowcount or 0
    await session.execute(delete(VesselPosition).where(VesselPosition.updated_at < now - RETENTION))
    await session.commit()
    return written


class Socket(Protocol):
    async def send(self, message: str) -> None: ...
    async def recv(self) -> str | bytes: ...


class VesselStream:
    def __init__(
        self,
        api_key: str,
        sessions: async_sessionmaker[AsyncSession],
        # Returns an async context manager yielding a Socket
        connect: Callable[[], Any],
        max_boxes: int,
        box_degrees: float,
    ) -> None:
        self.api_key = api_key
        self.sessions = sessions
        self.connect = connect
        self.max_boxes = max_boxes
        self.box_degrees = box_degrees
        self.pending: dict[int, VesselUpdate] = {}

    async def _subscription(self) -> str | None:
        async with self.sessions() as session:
            points = await watched_points(session, self.max_boxes)
        if not points:
            return None
        return json.dumps(
            {
                "APIKey": self.api_key,
                "BoundingBoxes": subscription_boxes(points, self.box_degrees, self.max_boxes),
                "FilterMessageTypes": MESSAGE_TYPES,
            }
        )

    def accept(self, raw: str | bytes) -> None:
        update = parse_message(raw)
        if update is None:
            return
        previous = self.pending.get(update.mmsi)
        self.pending[update.mmsi] = previous.merge(update) if previous else update

    async def flush(self) -> int:
        if not self.pending:
            return 0
        batch, self.pending = list(self.pending.values()), {}
        async with self.sessions() as session:
            return await store(session, batch, datetime.now(UTC))

    async def run_once(self) -> None:
        """One connection: subscribe, then read until it drops."""
        subscription = await self._subscription()
        if subscription is None:
            logger.info("AIS: no active high/critical events to watch")
            await asyncio.sleep(RESUBSCRIBE_SECONDS)
            return
        async with self.connect() as socket:
            await socket.send(subscription)  # AISStream requires it within 3 s
            loop = asyncio.get_running_loop()
            next_flush = loop.time() + FLUSH_SECONDS
            next_subscription = loop.time() + RESUBSCRIBE_SECONDS
            while True:
                try:
                    raw = await asyncio.wait_for(socket.recv(), timeout=FLUSH_SECONDS)
                    self.accept(raw)
                except TimeoutError:
                    pass
                now = loop.time()
                if now >= next_flush:
                    await self.flush()
                    next_flush = now + FLUSH_SECONDS
                if now >= next_subscription:
                    updated = await self._subscription()
                    if updated:
                        await socket.send(updated)
                    next_subscription = now + RESUBSCRIBE_SECONDS

    async def run_forever(self) -> None:
        backoff = 5
        while True:
            try:
                await self.run_once()
                backoff = 5
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.warning("AIS stream error, retrying in %ss: %r", backoff, e)
                await asyncio.sleep(backoff)
                backoff = min(MAX_BACKOFF_SECONDS, backoff * 2)
            finally:
                try:
                    await self.flush()
                except Exception:
                    logger.exception("AIS flush failed")


async def vessels_geojson(
    session: AsyncSession, bbox: tuple[float, float, float, float], max_age: timedelta, limit: int
) -> dict[str, Any]:
    cutoff = datetime.now(UTC) - max_age
    rows = await session.execute(
        select(VesselPosition)
        .where(envelope_filter(VesselPosition.location, *bbox), VesselPosition.updated_at >= cutoff)
        .order_by(VesselPosition.updated_at.desc())
        .limit(limit)
    )
    features = [
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [round(v.longitude, 5), round(v.latitude, 5)]},
            "properties": {
                "mmsi": v.mmsi,
                "name": v.name,
                "ship_type": v.ship_type,
                "speed_kn": v.speed_kn,
                "course_deg": v.course_deg,
                "heading_deg": v.heading_deg,
                "updated_at": v.updated_at.isoformat(),
            },
        }
        for v in rows.scalars()
    ]
    return {"type": "FeatureCollection", "features": features}
