"""Periodic ingestion jobs (GDACS, Copernicus, USGS, EONET, FIRMS).

Every job runs through `_run`, which provides the shared behaviour:
- a PostgreSQL advisory lock so only one worker/replica runs each job;
- commit on success, and failure recording on the data source otherwise
  (shown in the source status panel);
- in-memory status for GET /scheduler/status.
"""

import logging
import zlib
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.database import async_session_maker
from src.repositories.data_source_repository import DataSourceRepository
from src.services.copernicus_service import CopernicusEMSService
from src.services.gdacs_service import GDACSService
from src.services.hazards.firms import ingest_firms
from src.services.ingestion_service import IngestionService

logger = logging.getLogger(__name__)

# Consecutive failures after which a job is logged as critical
CRITICAL_AFTER_FAILURES = 3


def _job_lock_key(job: str) -> int:
    """Stable advisory-lock key per job (crc32 fits PostgreSQL's bigint key)."""
    return zlib.crc32(f"phoenix-sync:{job}".encode())


@dataclass
class JobStatus:
    last_sync: datetime | None = None
    last_error: str | None = None
    sync_count: int = 0
    consecutive_failures: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "last_sync": self.last_sync.isoformat() if self.last_sync else None,
            "last_error": self.last_error,
            "sync_count": self.sync_count,
            "consecutive_failures": self.consecutive_failures,
        }


# job key -> data source name (as stored in data_sources)
JOBS = {
    "gdacs": "GDACS",
    "copernicus": "Copernicus",
    "usgs": "USGS",
    "eonet": "EONET",
    "firms": "NASA FIRMS",
}

Work = Callable[[AsyncSession], Awaitable[dict[str, Any]]]


class SchedulerService:
    _instance: "SchedulerService | None" = None
    _scheduler: AsyncIOScheduler | None = None

    def __new__(cls) -> "SchedulerService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if self._scheduler is None:
            self._scheduler = AsyncIOScheduler()
            self._gdacs_service = GDACSService()
            self._copernicus_service = CopernicusEMSService()
            self._status = {job: JobStatus() for job in JOBS}

    @asynccontextmanager
    async def _exclusive_job(self, job: str) -> AsyncIterator[AsyncSession | None]:
        """Yield a session holding the job's advisory lock, or None if taken.

        Every API worker/replica runs its own scheduler; without this each one
        would ingest the same feed concurrently. pg_try_advisory_xact_lock is
        released automatically at commit/rollback, including if the process
        dies, so a crashed worker can never leave a stale lock.
        """
        async with async_session_maker() as session:
            acquired = (
                await session.execute(
                    text("SELECT pg_try_advisory_xact_lock(:key)"),
                    {"key": _job_lock_key(job)},
                )
            ).scalar()
            if not acquired:
                logger.info("Skipping %s sync: another worker is running it", job)
                yield None
                return
            yield session

    async def _record_failure(self, source_name: str, error: Exception) -> None:
        """Persist a failed sync so the source status panel can show it.

        Best effort: a database outage must not crash the scheduler job.
        """
        try:
            async with async_session_maker() as session:
                repo = DataSourceRepository(session)
                source = await repo.get_by_name(source_name)
                if source is None:
                    return  # never synced successfully; nothing to mark yet
                await repo.update_sync_status(
                    source.id,
                    last_sync=datetime.now(timezone.utc),
                    status="failed",
                    # Public status endpoint shows this: exception type only
                    error=type(error).__name__,
                )
                await session.commit()
        except Exception:
            logger.exception("Could not record %s sync failure", source_name)

    async def _run(self, job: str, work: Work) -> None:
        """Run one job under its lock; never raises (a job must not kill the scheduler)."""
        status = self._status[job]
        try:
            # The lock is taken before fetching so losing workers skip the download
            async with self._exclusive_job(job) as session:
                if session is None:
                    return
                result = await work(session)
                await session.commit()  # also releases the lock
        except Exception as e:
            await self._record_failure(JOBS[job], e)
            status.consecutive_failures += 1
            status.last_error = str(e)
            critical = status.consecutive_failures >= CRITICAL_AFTER_FAILURES
            logger.log(
                logging.CRITICAL if critical else logging.ERROR,
                "%s sync failed (%d consecutive): %r",
                job,
                status.consecutive_failures,
                e,
                exc_info=critical,
            )
            return
        status.last_sync = datetime.now(timezone.utc)
        status.last_error = None
        status.sync_count += 1
        status.consecutive_failures = 0
        logger.info("%s sync #%d completed: %s", job, status.sync_count, result)

    # --- jobs -------------------------------------------------------------

    async def sync_gdacs(self) -> None:
        async def work(session: AsyncSession) -> dict[str, Any]:
            events = await self._gdacs_service.fetch_rss_events()
            return await IngestionService(session).ingest_gdacs_events(events, atomic=False)

        await self._run("gdacs", work)

    async def sync_copernicus(self) -> None:
        async def work(session: AsyncSession) -> dict[str, Any]:
            events = await self._copernicus_service.fetch_activations()
            return await IngestionService(session).ingest_copernicus_events(events, atomic=False)

        await self._run("copernicus", work)

    async def sync_usgs(self) -> None:
        from src.services.connectors.usgs_connector import USGSConnector

        async def work(session: AsyncSession) -> dict[str, Any]:
            events = await USGSConnector(feed="4.5_week").fetch_events()  # M4.5+, past week
            return await IngestionService(session).ingest_usgs_events(events, atomic=False)

        await self._run("usgs", work)

    async def sync_eonet(self) -> None:
        from src.services.connectors.eonet_connector import EONETConnector

        async def work(session: AsyncSession) -> dict[str, Any]:
            events = await EONETConnector(status="open", days=30).fetch_events()
            return await IngestionService(session).ingest_eonet_events(events, atomic=False)

        await self._run("eonet", work)

    async def sync_firms(self) -> None:
        """NASA FIRMS active fires (keyless 24 h files) into PostGIS."""

        async def work(session: AsyncSession) -> dict[str, Any]:
            result = await ingest_firms(session)
            repo = DataSourceRepository(session)
            source = await repo.get_or_create(
                name="NASA FIRMS",
                type="satellite",
                defaults={
                    "api_url": "https://firms.modaps.eosdis.nasa.gov/active_fire/",
                    "update_frequency": "30 minutes",
                    "sync_interval_minutes": 30,
                    "is_realtime": True,
                },
            )
            await repo.update_sync_status(
                source.id, last_sync=datetime.now(timezone.utc), status="success"
            )
            return result

        await self._run("firms", work)

    # --- lifecycle ----------------------------------------------------------

    def start(self, sync_interval_minutes: int = 5) -> None:
        if self._scheduler is None:
            return
        schedule = [
            (self.sync_gdacs, sync_interval_minutes, "GDACS Event Sync"),
            (self.sync_copernicus, sync_interval_minutes, "Copernicus EMS Sync"),
            (self.sync_usgs, sync_interval_minutes, "USGS Earthquake Sync"),
            (self.sync_eonet, 10, "EONET Event Sync"),  # natural events change slowly
            (self.sync_firms, 30, "NASA FIRMS Active Fires"),  # files refresh every few hours
        ]
        for job, minutes, name in schedule:
            self._scheduler.add_job(
                job,
                trigger=IntervalTrigger(minutes=minutes),
                id=f"{job.__name__.removeprefix('sync_')}_sync",
                name=name,
                replace_existing=True,
            )
        self._scheduler.start()
        logger.info("Scheduler started with %d jobs", len(schedule))

    def stop(self) -> None:
        if self._scheduler is not None and self._scheduler.running:
            self._scheduler.shutdown(wait=False)
            logger.info("Scheduler stopped")

    def get_status(self) -> dict[str, Any]:
        return {
            "running": self._scheduler.running if self._scheduler else False,
            **{job: status.as_dict() for job, status in self._status.items()},
        }


scheduler_service = SchedulerService()
