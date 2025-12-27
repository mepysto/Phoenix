import logging
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from src.core.exceptions import DataSyncError, ExternalAPIError
from src.services.gdacs_service import GDACSService

logger = logging.getLogger(__name__)


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
            self._last_sync: datetime | None = None
            self._last_sync_error: str | None = None
            self._sync_count = 0
            self._consecutive_failures = 0

    async def sync_gdacs(self) -> None:
        """
        Synchronize GDACS events with error handling.

        This method catches all exceptions to prevent the scheduler from stopping.
        Errors are logged with appropriate severity levels.
        """
        try:
            logger.info("Starting GDACS sync...")
            count = await self._gdacs_service.sync_events()
            self._last_sync = datetime.now(timezone.utc)
            self._last_sync_error = None
            self._sync_count += 1
            self._consecutive_failures = 0
            logger.info(f"GDACS sync completed: {count} events fetched (sync #{self._sync_count})")

        except DataSyncError as e:
            self._consecutive_failures += 1
            self._last_sync_error = str(e)
            logger.error(
                f"GDACS sync failed after retries: {e} "
                f"(consecutive failures: {self._consecutive_failures})"
            )
            if self._consecutive_failures >= 3:
                logger.critical(
                    f"GDACS sync has failed {self._consecutive_failures} consecutive times. "
                    "Manual intervention may be required."
                )

        except ExternalAPIError as e:
            self._consecutive_failures += 1
            self._last_sync_error = str(e)
            logger.error(
                f"GDACS external API error: {e} "
                f"(consecutive failures: {self._consecutive_failures})"
            )

        except Exception as e:
            self._consecutive_failures += 1
            self._last_sync_error = str(e)
            logger.exception(
                f"Unexpected error during GDACS sync: {e} "
                f"(consecutive failures: {self._consecutive_failures})"
            )

    def start(self, sync_interval_minutes: int = 5) -> None:
        if self._scheduler is None:
            return

        self._scheduler.add_job(
            self.sync_gdacs,
            trigger=IntervalTrigger(minutes=sync_interval_minutes),
            id="gdacs_sync",
            name="GDACS Event Sync",
            replace_existing=True,
        )

        self._scheduler.start()
        logger.info(f"Scheduler started with {sync_interval_minutes}-minute sync interval")

    def stop(self) -> None:
        if self._scheduler is not None:
            self._scheduler.shutdown(wait=False)
            logger.info("Scheduler stopped")

    def get_status(self) -> dict[str, str | int | None]:
        return {
            "running": self._scheduler.running if self._scheduler else False,
            "last_sync": self._last_sync.isoformat() if self._last_sync else None,
            "last_sync_error": self._last_sync_error,
            "sync_count": self._sync_count,
            "consecutive_failures": self._consecutive_failures,
        }


scheduler_service = SchedulerService()
