"""Active fires from NASA LANCE FIRMS (keyless 24-hour global files).

FIRMS publishes rolling 24 h global CSVs per sensor without an API key. Each
ingest reads them, upserts new detections (idempotent via a unique key) and
prunes rows older than RETENTION_HOURS. ~220k VIIRS detections per day, so
rows are bulk-loaded with COPY into a temp table, then inserted.

Data policy: NASA open data; third-party redistribution must follow the LANCE
citation/disclaimer guidance (see docs/DATA_SOURCES.md).
"""

import csv
import io
import logging
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

BASE = "https://firms.modaps.eosdis.nasa.gov/data/active_fire"
FEEDS = {
    # VIIRS 375 m: far better small-fire detection than MODIS (1 km)
    "VIIRS S-NPP": f"{BASE}/suomi-npp-viirs-c2/csv/SUOMI_VIIRS_C2_Global_24h.csv",
    "VIIRS NOAA-20": f"{BASE}/noaa-20-viirs-c2/csv/J1_VIIRS_C2_Global_24h.csv",
}
RETENTION_HOURS = 48
REQUEST_TIMEOUT = httpx.Timeout(120.0, connect=15.0)


@dataclass(frozen=True)
class Detection:
    satellite: str
    instrument: str
    acquired_at: datetime
    latitude: float
    longitude: float
    frp: float | None
    brightness_k: float | None
    confidence: str | None
    daynight: str | None


def _float(value: str | None) -> float | None:
    try:
        return float(value) if value not in (None, "") else None
    except ValueError:
        return None


def parse_firms_csv(content: str) -> Iterator[Detection]:
    """Parse a FIRMS CSV (VIIRS or MODIS columns); bad rows are skipped."""
    for row in csv.DictReader(io.StringIO(content)):
        lat, lng = _float(row.get("latitude")), _float(row.get("longitude"))
        date, hhmm = row.get("acq_date"), (row.get("acq_time") or "").zfill(4)
        if lat is None or lng is None or not date or not hhmm.isdigit():
            continue
        if not (-90 <= lat <= 90 and -180 <= lng <= 180):
            continue
        try:
            acquired = datetime.strptime(f"{date} {hhmm}", "%Y-%m-%d %H%M").replace(tzinfo=UTC)
        except ValueError:
            continue
        brightness = row.get("bright_ti4") or row.get("brightness")  # VIIRS | MODIS
        yield Detection(
            satellite=(row.get("satellite") or "?").strip(),
            instrument="MODIS" if "brightness" in row else "VIIRS",
            acquired_at=acquired,
            latitude=lat,
            longitude=lng,
            frp=_float(row.get("frp")),
            brightness_k=_float(brightness),
            confidence=(row.get("confidence") or "").strip() or None,
            daynight=(row.get("daynight") or "").strip()[:1] or None,
        )


async def store_detections(session: AsyncSession, detections: Iterable[Detection]) -> int:
    """Bulk upsert via COPY into a temp table; returns newly inserted rows."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    count = 0
    for d in detections:
        writer.writerow(
            [d.satellite, d.instrument, d.acquired_at.isoformat(), d.latitude, d.longitude,
             "" if d.frp is None else d.frp, "" if d.brightness_k is None else d.brightness_k,
             d.confidence or "", d.daynight or ""]
        )
        count += 1
    if not count:
        return 0

    columns = "satellite, instrument, acquired_at, latitude, longitude, frp, brightness_k, confidence, daynight"
    # Several feeds load in one transaction, so drop explicitly after each
    await session.execute(
        text(f"CREATE TEMP TABLE fire_import ({columns.replace(', ', ' text, ')} text)")
    )
    raw = await (await session.connection()).get_raw_connection()
    await raw.driver_connection.copy_to_table(
        "fire_import", source=io.BytesIO(buffer.getvalue().encode()), format="csv"
    )
    result = await session.execute(
        text(
            f"""
            INSERT INTO fire_detections ({columns}, location)
            SELECT satellite, instrument, acquired_at::timestamptz, latitude::float8,
                   longitude::float8, NULLIF(frp, '')::float8, NULLIF(brightness_k, '')::float8,
                   NULLIF(confidence, ''), NULLIF(daynight, ''),
                   ST_SetSRID(ST_MakePoint(longitude::float8, latitude::float8), 4326)
            FROM fire_import
            ON CONFLICT (satellite, acquired_at, latitude, longitude) DO NOTHING
            """
        )
    )
    await session.execute(text("DROP TABLE fire_import"))
    return result.rowcount or 0


async def prune_old(session: AsyncSession, now: datetime | None = None) -> int:
    cutoff = (now or datetime.now(UTC)) - timedelta(hours=RETENTION_HOURS)
    result = await session.execute(
        text("DELETE FROM fire_detections WHERE acquired_at < :cutoff"), {"cutoff": cutoff}
    )
    return result.rowcount or 0


async def ingest_firms(session: AsyncSession, client: httpx.AsyncClient | None = None) -> dict:
    """Download every feed, store new detections, prune expired ones."""
    own_client = client is None
    client = client or httpx.AsyncClient(timeout=REQUEST_TIMEOUT, follow_redirects=True)
    inserted = 0
    # The "24 h" files still carry detections older than the retention window
    # (processing latency); skip them instead of inserting then pruning.
    cutoff = datetime.now(UTC) - timedelta(hours=RETENTION_HOURS)
    try:
        for name, url in FEEDS.items():
            response = await client.get(url)
            response.raise_for_status()
            fresh = (d for d in parse_firms_csv(response.text) if d.acquired_at >= cutoff)
            new = await store_detections(session, fresh)
            logger.info("FIRMS %s: %d new detections", name, new)
            inserted += new
    finally:
        if own_client:
            await client.aclose()
    pruned = await prune_old(session)
    return {"inserted": inserted, "pruned": pruned}
