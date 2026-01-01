import logging
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from src.core.exceptions import DataSyncError, ExternalAPIError
from src.db.database import async_session_maker
from src.services.copernicus_service import CopernicusEMSService
from src.services.gdacs_service import GDACSService
from src.services.ingestion_service import IngestionService

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
            self._copernicus_service = CopernicusEMSService()
            self._last_sync: datetime | None = None
            self._last_sync_error: str | None = None
            self._sync_count = 0
            self._consecutive_failures = 0
            # Copernicus specific tracking
            self._last_copernicus_sync: datetime | None = None
            self._last_copernicus_error: str | None = None
            self._copernicus_sync_count = 0
            self._copernicus_consecutive_failures = 0
            # USGS specific tracking
            self._last_usgs_sync: datetime | None = None
            self._last_usgs_error: str | None = None
            self._usgs_sync_count = 0
            self._usgs_consecutive_failures = 0
            # EONET specific tracking
            self._last_eonet_sync: datetime | None = None
            self._last_eonet_error: str | None = None
            self._eonet_sync_count = 0
            self._eonet_consecutive_failures = 0

    async def sync_gdacs(self) -> None:
        """
        Synchronize GDACS events with error handling and DB persistence.

        This method:
        1. Fetches events from GDACS RSS feed
        2. Opens a DB session and uses IngestionService to persist events
        3. Updates data_sources table with sync status
        4. Catches all exceptions to prevent the scheduler from stopping

        Errors are logged with appropriate severity levels.
        """
        try:
            logger.info("Starting GDACS sync...")

            # 1. Fetch events from GDACS
            events = await self._gdacs_service.fetch_rss_events()

            # 2. Open DB session and ingest events
            async with async_session_maker() as session:
                ingestion_service = IngestionService(session)
                result = await ingestion_service.ingest_gdacs_events(events, atomic=False)
                await session.commit()

            # 3. Update in-memory status
            self._last_sync = datetime.now(timezone.utc)
            self._last_sync_error = None
            self._sync_count += 1
            self._consecutive_failures = 0

            logger.info(
                f"GDACS sync completed: {result['created']} created, "
                f"{result['updated']} updated, {result['failed']} failed "
                f"(sync #{self._sync_count})"
            )

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

    async def sync_copernicus(self) -> None:
        """
        Synchronize Copernicus EMS events with error handling and DB persistence.

        This method:
        1. Fetches events from Copernicus EMS API
        2. Opens a DB session and uses IngestionService to persist events
        3. Updates data_sources table with sync status
        4. Catches all exceptions to prevent the scheduler from stopping

        Errors are logged with appropriate severity levels.
        """
        try:
            logger.info("Starting Copernicus EMS sync...")

            # 1. Fetch events from Copernicus
            events = await self._copernicus_service.fetch_activations()

            # 2. Open DB session and ingest events
            async with async_session_maker() as session:
                ingestion_service = IngestionService(session)
                result = await ingestion_service.ingest_copernicus_events(events, atomic=False)
                await session.commit()

            # 3. Update in-memory status
            self._last_copernicus_sync = datetime.now(timezone.utc)
            self._last_copernicus_error = None
            self._copernicus_sync_count += 1
            self._copernicus_consecutive_failures = 0

            logger.info(
                f"Copernicus EMS sync completed: {result['created']} created, "
                f"{result['updated']} updated, {result['failed']} failed "
                f"(sync #{self._copernicus_sync_count})"
            )

        except DataSyncError as e:
            self._copernicus_consecutive_failures += 1
            self._last_copernicus_error = str(e)
            logger.error(
                f"Copernicus EMS sync failed after retries: {e} "
                f"(consecutive failures: {self._copernicus_consecutive_failures})"
            )
            if self._copernicus_consecutive_failures >= 3:
                logger.critical(
                    f"Copernicus EMS sync has failed {self._copernicus_consecutive_failures} "
                    "consecutive times. Manual intervention may be required."
                )

        except ExternalAPIError as e:
            self._copernicus_consecutive_failures += 1
            self._last_copernicus_error = str(e)
            logger.error(
                f"Copernicus EMS external API error: {e} "
                f"(consecutive failures: {self._copernicus_consecutive_failures})"
            )

        except Exception as e:
            self._copernicus_consecutive_failures += 1
            self._last_copernicus_error = str(e)
            logger.exception(
                f"Unexpected error during Copernicus EMS sync: {e} "
                f"(consecutive failures: {self._copernicus_consecutive_failures})"
            )

    async def sync_usgs(self) -> None:
        """
        Synchronize USGS earthquake events with error handling and DB persistence.

        This method:
        1. Fetches earthquake events from USGS GeoJSON feed
        2. Opens a DB session and uses IngestionService to persist events
        3. Updates data_sources table with sync status
        4. Catches all exceptions to prevent the scheduler from stopping

        Errors are logged with appropriate severity levels.
        """
        try:
            from src.services.connectors.usgs_connector import USGSConnector

            logger.info("Starting USGS sync...")

            # 1. Fetch events from USGS (M4.5+ past week)
            connector = USGSConnector(feed="4.5_week")
            events = await connector.fetch_events()

            # 2. Open DB session and ingest events
            async with async_session_maker() as session:
                ingestion_service = IngestionService(session)
                result = await ingestion_service.ingest_usgs_events(events, atomic=False)
                await session.commit()

            # 3. Update in-memory status
            self._last_usgs_sync = datetime.now(timezone.utc)
            self._last_usgs_error = None
            self._usgs_sync_count += 1
            self._usgs_consecutive_failures = 0

            logger.info(
                f"USGS sync completed: {result['created']} created, "
                f"{result['updated']} updated, {result['failed']} failed "
                f"(sync #{self._usgs_sync_count})"
            )

        except DataSyncError as e:
            self._usgs_consecutive_failures += 1
            self._last_usgs_error = str(e)
            logger.error(
                f"USGS sync failed after retries: {e} "
                f"(consecutive failures: {self._usgs_consecutive_failures})"
            )
            if self._usgs_consecutive_failures >= 3:
                logger.critical(
                    f"USGS sync has failed {self._usgs_consecutive_failures} consecutive times. "
                    "Manual intervention may be required."
                )

        except ExternalAPIError as e:
            self._usgs_consecutive_failures += 1
            self._last_usgs_error = str(e)
            logger.error(
                f"USGS external API error: {e} "
                f"(consecutive failures: {self._usgs_consecutive_failures})"
            )

        except Exception as e:
            self._usgs_consecutive_failures += 1
            self._last_usgs_error = str(e)
            logger.exception(
                f"Unexpected error during USGS sync: {e} "
                f"(consecutive failures: {self._usgs_consecutive_failures})"
            )

    async def sync_eonet(self) -> None:
        """
        Synchronize NASA EONET events with error handling and DB persistence.

        This method:
        1. Fetches natural events from NASA EONET API
        2. Opens a DB session and uses IngestionService to persist events
        3. Updates data_sources table with sync status
        4. Catches all exceptions to prevent the scheduler from stopping

        Errors are logged with appropriate severity levels.
        """
        try:
            from src.services.connectors.eonet_connector import EONETConnector

            logger.info("Starting EONET sync...")

            # 1. Fetch events from EONET (open events, past 30 days)
            connector = EONETConnector(status="open", days=30)
            events = await connector.fetch_events()

            # 2. Open DB session and ingest events
            async with async_session_maker() as session:
                ingestion_service = IngestionService(session)
                result = await ingestion_service.ingest_eonet_events(events, atomic=False)
                await session.commit()

            # 3. Update in-memory status
            self._last_eonet_sync = datetime.now(timezone.utc)
            self._last_eonet_error = None
            self._eonet_sync_count += 1
            self._eonet_consecutive_failures = 0

            logger.info(
                f"EONET sync completed: {result['created']} created, "
                f"{result['updated']} updated, {result['failed']} failed "
                f"(sync #{self._eonet_sync_count})"
            )

        except DataSyncError as e:
            self._eonet_consecutive_failures += 1
            self._last_eonet_error = str(e)
            logger.error(
                f"EONET sync failed after retries: {e} "
                f"(consecutive failures: {self._eonet_consecutive_failures})"
            )
            if self._eonet_consecutive_failures >= 3:
                logger.critical(
                    f"EONET sync has failed {self._eonet_consecutive_failures} consecutive times. "
                    "Manual intervention may be required."
                )

        except ExternalAPIError as e:
            self._eonet_consecutive_failures += 1
            self._last_eonet_error = str(e)
            logger.error(
                f"EONET external API error: {e} "
                f"(consecutive failures: {self._eonet_consecutive_failures})"
            )

        except Exception as e:
            self._eonet_consecutive_failures += 1
            self._last_eonet_error = str(e)
            logger.exception(
                f"Unexpected error during EONET sync: {e} "
                f"(consecutive failures: {self._eonet_consecutive_failures})"
            )

    def start(self, sync_interval_minutes: int = 5) -> None:
        if self._scheduler is None:
            return

        # GDACS sync job
        self._scheduler.add_job(
            self.sync_gdacs,
            trigger=IntervalTrigger(minutes=sync_interval_minutes),
            id="gdacs_sync",
            name="GDACS Event Sync",
            replace_existing=True,
        )

        # Copernicus EMS sync job (offset by 2 minutes to avoid simultaneous requests)
        self._scheduler.add_job(
            self.sync_copernicus,
            trigger=IntervalTrigger(minutes=sync_interval_minutes),
            id="copernicus_sync",
            name="Copernicus EMS Sync",
            replace_existing=True,
        )

        # USGS sync job (every 5 minutes, earthquakes update frequently)
        self._scheduler.add_job(
            self.sync_usgs,
            trigger=IntervalTrigger(minutes=sync_interval_minutes),
            id="usgs_sync",
            name="USGS Earthquake Sync",
            replace_existing=True,
        )

        # EONET sync job (every 10 minutes, natural events update less frequently)
        self._scheduler.add_job(
            self.sync_eonet,
            trigger=IntervalTrigger(minutes=10),
            id="eonet_sync",
            name="EONET Event Sync",
            replace_existing=True,
        )

        self._scheduler.start()
        logger.info(
            f"Scheduler started with {sync_interval_minutes}-minute sync interval "
            "(GDACS + Copernicus EMS + USGS + EONET)"
        )

    def stop(self) -> None:
        if self._scheduler is not None:
            self._scheduler.shutdown(wait=False)
            logger.info("Scheduler stopped")

    def get_status(self) -> dict[str, str | int | None | dict]:
        """Get scheduler status from in-memory state.

        For DB-backed status including data_sources table info,
        use get_status_with_db() instead.
        """
        return {
            "running": self._scheduler.running if self._scheduler else False,
            "gdacs": {
                "last_sync": self._last_sync.isoformat() if self._last_sync else None,
                "last_error": self._last_sync_error,
                "sync_count": self._sync_count,
                "consecutive_failures": self._consecutive_failures,
            },
            "copernicus": {
                "last_sync": (
                    self._last_copernicus_sync.isoformat()
                    if self._last_copernicus_sync
                    else None
                ),
                "last_error": self._last_copernicus_error,
                "sync_count": self._copernicus_sync_count,
                "consecutive_failures": self._copernicus_consecutive_failures,
            },
            "usgs": {
                "last_sync": (
                    self._last_usgs_sync.isoformat() if self._last_usgs_sync else None
                ),
                "last_error": self._last_usgs_error,
                "sync_count": self._usgs_sync_count,
                "consecutive_failures": self._usgs_consecutive_failures,
            },
            "eonet": {
                "last_sync": (
                    self._last_eonet_sync.isoformat() if self._last_eonet_sync else None
                ),
                "last_error": self._last_eonet_error,
                "sync_count": self._eonet_sync_count,
                "consecutive_failures": self._eonet_consecutive_failures,
            },
        }

    async def get_status_with_db(self) -> dict[str, str | int | None | dict]:
        """Get scheduler status including data_sources table info.

        This method queries the database for the current status of
        each data source, providing persistent sync history.
        """
        from src.repositories.data_source_repository import DataSourceRepository

        status = self.get_status()

        try:
            async with async_session_maker() as session:
                repo = DataSourceRepository(session)

                # Get GDACS data source status
                gdacs_source = await repo.get_by_name("GDACS")
                if gdacs_source:
                    gdacs_status = status.get("gdacs")
                    if isinstance(gdacs_status, dict):
                        gdacs_status["db_last_sync"] = (
                            gdacs_source.last_sync.isoformat() if gdacs_source.last_sync else None
                        )
                        gdacs_status["db_last_sync_status"] = gdacs_source.last_sync_status
                        gdacs_status["db_consecutive_failures"] = gdacs_source.consecutive_failures

                # Get Copernicus data source status
                copernicus_source = await repo.get_by_name("Copernicus")
                if copernicus_source:
                    copernicus_status = status.get("copernicus")
                    if isinstance(copernicus_status, dict):
                        copernicus_status["db_last_sync"] = (
                            copernicus_source.last_sync.isoformat()
                            if copernicus_source.last_sync
                            else None
                        )
                        copernicus_status["db_last_sync_status"] = copernicus_source.last_sync_status
                        copernicus_status["db_consecutive_failures"] = (
                            copernicus_source.consecutive_failures
                        )

                # Get USGS data source status
                usgs_source = await repo.get_by_name("USGS")
                if usgs_source:
                    usgs_status = status.get("usgs")
                    if isinstance(usgs_status, dict):
                        usgs_status["db_last_sync"] = (
                            usgs_source.last_sync.isoformat() if usgs_source.last_sync else None
                        )
                        usgs_status["db_last_sync_status"] = usgs_source.last_sync_status
                        usgs_status["db_consecutive_failures"] = usgs_source.consecutive_failures

                # Get EONET data source status
                eonet_source = await repo.get_by_name("EONET")
                if eonet_source:
                    eonet_status = status.get("eonet")
                    if isinstance(eonet_status, dict):
                        eonet_status["db_last_sync"] = (
                            eonet_source.last_sync.isoformat() if eonet_source.last_sync else None
                        )
                        eonet_status["db_last_sync_status"] = eonet_source.last_sync_status
                        eonet_status["db_consecutive_failures"] = eonet_source.consecutive_failures

        except Exception as e:
            logger.warning(f"Failed to fetch DB status for data sources: {e}")
            status["db_error"] = str(e)

        return status


scheduler_service = SchedulerService()
