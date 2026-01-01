"""IngestionService for storing GDACS/Copernicus events to database."""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.event import EventType, GeoPrecision, GeoMethod, SeverityLevel
from src.repositories import DataSourceRepository, EventRepository, EventSourceRepository
from src.services.connectors.base import RawEvent
from src.services.copernicus_service import CopernicusEvent
from src.services.dedup import DedupService
from src.services.gdacs_service import GDACSEvent
from src.services.normalization.severity import get_severity_strategy

logger = logging.getLogger(__name__)

# GDACS event type mapping
GDACS_EVENT_TYPE_MAP: dict[str, EventType] = {
    "earthquake": EventType.earthquake,
    "flood": EventType.flood,
    "hurricane": EventType.hurricane,
    "volcano": EventType.volcano,
    "drought": EventType.drought,
    "wildfire": EventType.wildfire,
    "tsunami": EventType.tsunami,
    "other": EventType.other,
}

# GDACS severity mapping
GDACS_SEVERITY_MAP: dict[str, SeverityLevel] = {
    "low": SeverityLevel.low,
    "medium": SeverityLevel.medium,
    "high": SeverityLevel.high,
    "critical": SeverityLevel.critical,
}

# Copernicus event type mapping
COPERNICUS_EVENT_TYPE_MAP: dict[str, EventType] = {
    "flood": EventType.flood,
    "hurricane": EventType.hurricane,
    "wildfire": EventType.wildfire,
    "earthquake": EventType.earthquake,
    "volcano": EventType.volcano,
    "drought": EventType.drought,
    "landslide": EventType.landslide,
    "tsunami": EventType.tsunami,
    "industrial": EventType.industrial,
    "other": EventType.other,
}

# Copernicus severity mapping
COPERNICUS_SEVERITY_MAP: dict[str, SeverityLevel] = {
    "low": SeverityLevel.low,
    "medium": SeverityLevel.medium,
    "high": SeverityLevel.high,
    "critical": SeverityLevel.critical,
}

# USGS event type mapping (earthquakes only)
USGS_EVENT_TYPE_MAP: dict[str, EventType] = {
    "earthquake": EventType.earthquake,
}

# EONET event type mapping (from EONET category to EventType)
EONET_EVENT_TYPE_MAP: dict[str, EventType] = {
    "drought": EventType.drought,
    "earthquake": EventType.earthquake,
    "flood": EventType.flood,
    "landslide": EventType.landslide,
    "industrial": EventType.industrial,
    "storm": EventType.storm,
    "heatwave": EventType.heatwave,
    "volcano": EventType.volcano,
    "wildfire": EventType.wildfire,
    "pollution": EventType.pollution,
    "other": EventType.other,
}


@dataclass
class IngestionResult:
    """Result of an ingestion operation."""

    created: int = 0
    updated: int = 0
    failed: int = 0
    errors: list[str] | None = None

    def __post_init__(self) -> None:
        """Initialize errors list if None."""
        if self.errors is None:
            self.errors = []

    def add_error(self, error: str) -> None:
        """Add an error message to the errors list."""
        if self.errors is None:
            self.errors = []
        self.errors.append(error)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "created": self.created,
            "updated": self.updated,
            "failed": self.failed,
            "errors": self.errors or [],
        }


class IngestionService:
    """Service for ingesting external disaster events into the database."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize IngestionService with database session.

        Args:
            session: SQLAlchemy async session for database operations
        """
        self.session = session
        self.data_source_repo = DataSourceRepository(session)
        self.event_repo = EventRepository(session)
        self.event_source_repo = EventSourceRepository(session)
        self.dedup_service = DedupService(session)

    async def ingest_raw_events(
        self,
        events: list[RawEvent],
        source_name: str,
        event_type_map: dict[str, EventType],
        data_source_defaults: dict[str, Any],
        atomic: bool = True,
    ) -> IngestionResult:
        """Generic RawEvent ingestion method.

        This method provides a unified way to ingest events from any connector
        that produces RawEvent instances. It handles:
        1. DataSource get_or_create
        2. Severity computation using source-specific strategies
        3. Event creation/update with deduplication
        4. EventSource linking

        Args:
            events: List of RawEvent instances to ingest
            source_name: Name of the data source (e.g., "USGS", "EONET")
            event_type_map: Mapping from event_type_raw to EventType enum
            data_source_defaults: Default values for DataSource creation
            atomic: If True, all events in one transaction (rollback on failure).
                   If False, process individually (skip failures).

        Returns:
            IngestionResult with created/updated/failed counts
        """
        result = IngestionResult(errors=[])

        if not events:
            return result

        try:
            # Get or create the data source
            data_source = await self.data_source_repo.get_or_create(
                name=source_name,
                type=data_source_defaults.get("type", "disaster_alert"),
                defaults=data_source_defaults,
            )

            # Get severity strategy for this source
            severity_strategy = get_severity_strategy(source_name)

            for raw_event in events:
                try:
                    await self._process_raw_event(
                        raw_event=raw_event,
                        data_source_id=data_source.id,
                        event_type_map=event_type_map,
                        severity_strategy=severity_strategy,
                        result=result,
                    )
                except Exception as e:
                    error_msg = f"Failed to process {source_name} event {raw_event.external_id}: {e}"
                    logger.error(error_msg)
                    result.failed += 1
                    result.add_error(error_msg)

                    if atomic:
                        # In atomic mode, re-raise to trigger rollback
                        raise

            # Update sync status on success
            await self.data_source_repo.update_sync_status(
                data_source.id,
                last_sync=datetime.now(timezone.utc),
                status="success",
            )

        except Exception as e:
            if atomic:
                # Let the exception propagate for rollback
                raise
            error_msg = f"{source_name} ingestion error: {e}"
            logger.error(error_msg)
            result.add_error(error_msg)

        return result

    async def _process_raw_event(
        self,
        raw_event: RawEvent,
        data_source_id: Any,
        event_type_map: dict[str, EventType],
        severity_strategy: Any,
        result: IngestionResult,
    ) -> None:
        """Process a single RawEvent.

        This method implements cross-source deduplication:
        1. Check if event exists for THIS SOURCE (same-source dedup)
        2. If not, try cross-source matching via DedupService
        3. If match found, merge into existing event
        4. If no match, create new event

        Args:
            raw_event: The RawEvent to process
            data_source_id: UUID of the data source
            event_type_map: Mapping from event_type_raw to EventType
            severity_strategy: Strategy for computing severity
            result: IngestionResult to update with counts
        """
        fetched_at = datetime.now(timezone.utc)

        # Map event type
        event_type = event_type_map.get(
            (raw_event.event_type_raw or "").lower(),
            EventType.other,
        )

        # Compute severity using source-specific strategy
        severity = severity_strategy.compute(raw_event)

        # Determine geo precision
        geo_precision = (
            GeoPrecision.approximate
            if raw_event.lat is not None and raw_event.lng is not None
            else GeoPrecision.unknown
        )

        # 1. Check if this event already exists for THIS SOURCE
        existing_event_id = await self.event_source_repo.find_event_id_by_source_external(
            source_id=data_source_id,
            external_id=raw_event.external_id,
        )

        if existing_event_id is None:
            # 2. Try cross-source matching via DedupService
            match = await self.dedup_service.find_matching_event(
                raw_event, event_type, geo_precision
            )

            if match is not None:
                # 3. Found match from DIFFERENT source - merge into existing event
                await self._merge_into_existing_event(
                    raw_event=raw_event,
                    match_event_id=match.event_id,
                    match_method=match.method,
                    data_source_id=data_source_id,
                    severity=severity,
                    geo_precision=geo_precision,
                    fetched_at=fetched_at,
                    result=result,
                )
                return

            # 4. No match found - create new event
            event = await self.event_repo.create(
                type=event_type,
                title=raw_event.title,
                description=raw_event.description,
                lat=raw_event.lat,
                lng=raw_event.lng,
                region=raw_event.country,
                severity=severity,
                start_date=raw_event.start_date,
                end_date=raw_event.end_date,
                source_id=raw_event.external_id,  # legacy field
                source_url=raw_event.source_url,
                is_active=raw_event.end_date is None,  # Active if no end date
                geo_precision=geo_precision,
                geo_method=GeoMethod.source_provided,
                glide_number=raw_event.glide_number,
            )

            # Create event source link
            await self.event_source_repo.upsert(
                source_id=data_source_id,
                external_id=raw_event.external_id,
                event_id=event.id,
                raw_data=raw_event.raw_data,
                fetched_at=fetched_at,
            )

            result.created += 1
            logger.debug(f"Created {raw_event.source_name} event: {raw_event.external_id}")

        else:
            # 5. Update existing (same source) - existing logic
            await self.event_source_repo.upsert(
                source_id=data_source_id,
                external_id=raw_event.external_id,
                event_id=existing_event_id,
                raw_data=raw_event.raw_data,
                fetched_at=fetched_at,
            )

            # Try to update the event if we have better data
            update_result = await self.event_repo.update_if_better(
                existing_event_id,
                {
                    "title": raw_event.title,
                    "description": raw_event.description,
                    "lat": raw_event.lat,
                    "lng": raw_event.lng,
                    "region": raw_event.country,
                    "severity": severity,
                    "source_url": raw_event.source_url,
                    "geo_precision": geo_precision,
                    "geo_method": GeoMethod.source_provided,
                    "end_date": raw_event.end_date,
                    "is_active": raw_event.end_date is None,
                },
            )

            if update_result is not None:
                result.updated += 1
                logger.debug(f"Updated {raw_event.source_name} event: {raw_event.external_id}")
            else:
                # Event source was updated but event data wasn't improved
                result.updated += 1
                logger.debug(f"Refreshed {raw_event.source_name} event source: {raw_event.external_id}")

    async def _merge_into_existing_event(
        self,
        raw_event: RawEvent,
        match_event_id: Any,
        match_method: str,
        data_source_id: Any,
        severity: SeverityLevel,
        geo_precision: GeoPrecision,
        fetched_at: datetime,
        result: IngestionResult,
    ) -> None:
        """Merge incoming event into an existing event from a different source.

        Args:
            raw_event: The incoming RawEvent
            match_event_id: UUID of the matched existing event
            match_method: How the match was found (strong_key, fuzzy)
            data_source_id: UUID of the incoming data source
            severity: Computed severity for incoming event
            geo_precision: Determined geo precision
            fetched_at: Fetch timestamp
            result: IngestionResult to update
        """
        # Get existing event with sources for quality scoring
        existing_event = await self.dedup_service.get_event_with_sources(match_event_id)
        if existing_event is None:
            # Edge case: event was deleted between match and fetch
            logger.warning(
                f"Matched event {match_event_id} no longer exists, creating new event"
            )
            return

        # Compute quality scores
        incoming_quality = self.dedup_service.compute_incoming_quality(
            raw_event, geo_precision
        )
        existing_quality = self.dedup_service.compute_existing_quality(existing_event)

        logger.debug(
            f"Quality scores for {raw_event.external_id}: "
            f"incoming={incoming_quality.total:.3f}, existing={existing_quality.total:.3f}"
        )

        # Build incoming data dict for merge
        incoming_data = {
            "title": raw_event.title,
            "description": raw_event.description,
            "lat": raw_event.lat,
            "lng": raw_event.lng,
            "region": raw_event.country,
            "severity": severity,
            "geo_precision": geo_precision,
            "geo_method": GeoMethod.source_provided,
            "glide_number": raw_event.glide_number,
            "source_url": raw_event.source_url,
        }

        # Build merge patch
        merge_patch = self.dedup_service.build_merge_patch(
            existing_event,
            incoming_data,
            incoming_quality.total,
            existing_quality.total,
        )

        # Apply merge if needed
        if merge_patch:
            await self.event_repo.update(match_event_id, **merge_patch.fields)
            logger.debug(
                f"Applied merge patch to event {match_event_id}: "
                f"updated fields={merge_patch.updated_field_names}"
            )

        # Link EventSource to existing event (cross-source link!)
        await self.event_source_repo.upsert(
            source_id=data_source_id,
            external_id=raw_event.external_id,
            event_id=match_event_id,
            raw_data=raw_event.raw_data,
            fetched_at=fetched_at,
        )

        result.updated += 1
        logger.info(
            f"Merged {raw_event.source_name} event {raw_event.external_id} "
            f"into existing event {match_event_id} via {match_method}"
        )

    async def ingest_usgs_events(
        self,
        events: list[RawEvent],
        atomic: bool = True,
    ) -> dict[str, Any]:
        """Ingest USGS earthquake events into the database.

        Args:
            events: List of RawEvent objects from USGS connector
            atomic: If True, all events in one transaction (rollback on failure).
                   If False, process individually (skip failures).

        Returns:
            Dictionary with created, updated, failed counts and errors list
        """
        result = await self.ingest_raw_events(
            events=events,
            source_name="USGS",
            event_type_map=USGS_EVENT_TYPE_MAP,
            data_source_defaults={
                "type": "disaster_alert",
                "api_url": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/geojson.php",
                "update_frequency": "1 minute",
                "sync_interval_minutes": 5,
                "is_realtime": True,
            },
            atomic=atomic,
        )
        return result.to_dict()

    async def ingest_eonet_events(
        self,
        events: list[RawEvent],
        atomic: bool = True,
    ) -> dict[str, Any]:
        """Ingest NASA EONET events into the database.

        Args:
            events: List of RawEvent objects from EONET connector
            atomic: If True, all events in one transaction (rollback on failure).
                   If False, process individually (skip failures).

        Returns:
            Dictionary with created, updated, failed counts and errors list
        """
        result = await self.ingest_raw_events(
            events=events,
            source_name="EONET",
            event_type_map=EONET_EVENT_TYPE_MAP,
            data_source_defaults={
                "type": "disaster_alert",
                "api_url": "https://eonet.gsfc.nasa.gov/api/v3",
                "update_frequency": "15 minutes",
                "sync_interval_minutes": 10,
                "is_realtime": False,
            },
            atomic=atomic,
        )
        return result.to_dict()

    async def ingest_gdacs_events(
        self,
        events: list[GDACSEvent],
        atomic: bool = True,
    ) -> dict[str, Any]:
        """Ingest GDACS events into the database.

        Process:
        1. Get or create DataSource "GDACS"
        2. For each event:
           - Look up existing event by (source_id, external_id) in event_sources
           - If not found: Create Event + EventSource
           - If found: Upsert EventSource + Update Event if better data

        Args:
            events: List of GDACSEvent objects from GDACS service
            atomic: If True, all events in one transaction (rollback on failure).
                   If False, process individually (skip failures).

        Returns:
            Dictionary with created, updated, failed counts and errors list
        """
        result = IngestionResult(errors=[])

        if not events:
            return result.to_dict()

        try:
            # Get or create the GDACS data source
            data_source = await self.data_source_repo.get_or_create(
                name="GDACS",
                type="disaster_alert",
                defaults={
                    "api_url": "https://www.gdacs.org/xml/rss.xml",
                    "update_frequency": "5 minutes",
                    "sync_interval_minutes": 5,
                    "is_realtime": False,
                },
            )

            for gdacs_event in events:
                try:
                    await self._process_gdacs_event(gdacs_event, data_source.id, result)
                except Exception as e:
                    error_msg = f"Failed to process GDACS event {gdacs_event.external_id}: {e}"
                    logger.error(error_msg)
                    result.failed += 1
                    result.add_error(error_msg)

                    if atomic:
                        # In atomic mode, re-raise to trigger rollback
                        raise

            # Update sync status on success
            await self.data_source_repo.update_sync_status(
                data_source.id,
                last_sync=datetime.now(timezone.utc),
                status="success",
            )

        except Exception as e:
            if atomic:
                # Let the exception propagate for rollback
                raise
            error_msg = f"GDACS ingestion error: {e}"
            logger.error(error_msg)
            result.add_error(error_msg)

        return result.to_dict()

    async def _process_gdacs_event(
        self,
        gdacs_event: GDACSEvent,
        data_source_id: Any,
        result: IngestionResult,
    ) -> None:
        """Process a single GDACS event.

        Args:
            gdacs_event: The GDACS event to process
            data_source_id: UUID of the GDACS data source
            result: IngestionResult to update with counts
        """
        fetched_at = datetime.now(timezone.utc)

        # Check if this event already exists
        existing_event_id = await self.event_source_repo.find_event_id_by_source_external(
            source_id=data_source_id,
            external_id=gdacs_event.external_id,
        )

        if existing_event_id is None:
            # Create new event
            event = await self.event_repo.create(
                type=self._map_gdacs_event_type(gdacs_event.event_type),
                title=gdacs_event.title,
                description=gdacs_event.description,
                lat=gdacs_event.lat,
                lng=gdacs_event.lng,
                region=gdacs_event.country,
                severity=self._map_gdacs_severity(gdacs_event.severity),
                affected_population=gdacs_event.population,
                start_date=gdacs_event.start_date,
                source_id=gdacs_event.external_id,  # legacy field
                source_url=gdacs_event.url,
                is_active=True,
                geo_precision=GeoPrecision.approximate,
                geo_method=GeoMethod.source_provided,
            )

            # Create event source link
            await self.event_source_repo.upsert(
                source_id=data_source_id,
                external_id=gdacs_event.external_id,
                event_id=event.id,
                raw_data=gdacs_event.raw_data,
                fetched_at=fetched_at,
            )

            result.created += 1
            logger.debug(f"Created GDACS event: {gdacs_event.external_id}")

        else:
            # Update existing event source with fresh data
            await self.event_source_repo.upsert(
                source_id=data_source_id,
                external_id=gdacs_event.external_id,
                event_id=existing_event_id,
                raw_data=gdacs_event.raw_data,
                fetched_at=fetched_at,
            )

            # Try to update the event if we have better data
            update_result = await self.event_repo.update_if_better(
                existing_event_id,
                {
                    "title": gdacs_event.title,
                    "description": gdacs_event.description,
                    "lat": gdacs_event.lat,
                    "lng": gdacs_event.lng,
                    "region": gdacs_event.country,
                    "severity": self._map_gdacs_severity(gdacs_event.severity),
                    "affected_population": gdacs_event.population,
                    "source_url": gdacs_event.url,
                    "geo_precision": GeoPrecision.approximate,
                    "geo_method": GeoMethod.source_provided,
                },
            )

            if update_result is not None:
                result.updated += 1
                logger.debug(f"Updated GDACS event: {gdacs_event.external_id}")
            else:
                # Event source was updated but event data wasn't improved
                result.updated += 1
                logger.debug(f"Refreshed GDACS event source: {gdacs_event.external_id}")

    async def ingest_copernicus_events(
        self,
        events: list[CopernicusEvent],
        atomic: bool = True,
    ) -> dict[str, Any]:
        """Ingest Copernicus EMS events into the database.

        Process:
        1. Get or create DataSource "Copernicus"
        2. For each event:
           - Look up existing event by (source_id, external_id) in event_sources
           - If not found: Create Event + EventSource
           - If found: Upsert EventSource + Update Event if better data

        Args:
            events: List of CopernicusEvent objects from Copernicus service
            atomic: If True, all events in one transaction (rollback on failure).
                   If False, process individually (skip failures).

        Returns:
            Dictionary with created, updated, failed counts and errors list
        """
        result = IngestionResult(errors=[])

        if not events:
            return result.to_dict()

        try:
            # Get or create the Copernicus data source
            data_source = await self.data_source_repo.get_or_create(
                name="Copernicus",
                type="satellite",
                defaults={
                    "api_url": "https://mapping.emergency.copernicus.eu/activations/api/activations/",
                    "update_frequency": "30 minutes",
                    "sync_interval_minutes": 30,
                    "is_realtime": False,
                },
            )

            for copernicus_event in events:
                try:
                    await self._process_copernicus_event(
                        copernicus_event, data_source.id, result
                    )
                except Exception as e:
                    error_msg = f"Failed to process Copernicus event {copernicus_event.external_id}: {e}"
                    logger.error(error_msg)
                    result.failed += 1
                    result.add_error(error_msg)

                    if atomic:
                        # In atomic mode, re-raise to trigger rollback
                        raise

            # Update sync status on success
            await self.data_source_repo.update_sync_status(
                data_source.id,
                last_sync=datetime.now(timezone.utc),
                status="success",
            )

        except Exception as e:
            if atomic:
                # Let the exception propagate for rollback
                raise
            error_msg = f"Copernicus ingestion error: {e}"
            logger.error(error_msg)
            result.add_error(error_msg)

        return result.to_dict()

    async def _process_copernicus_event(
        self,
        copernicus_event: CopernicusEvent,
        data_source_id: Any,
        result: IngestionResult,
    ) -> None:
        """Process a single Copernicus event.

        Args:
            copernicus_event: The Copernicus event to process
            data_source_id: UUID of the Copernicus data source
            result: IngestionResult to update with counts
        """
        fetched_at = datetime.now(timezone.utc)

        # Check if this event already exists
        existing_event_id = await self.event_source_repo.find_event_id_by_source_external(
            source_id=data_source_id,
            external_id=copernicus_event.external_id,
        )

        if existing_event_id is None:
            # Create new event
            event = await self.event_repo.create(
                type=self._map_copernicus_event_type(copernicus_event.event_type),
                title=copernicus_event.title,
                description=copernicus_event.description,
                lat=copernicus_event.lat,
                lng=copernicus_event.lng,
                region=copernicus_event.country,
                severity=self._map_copernicus_severity(copernicus_event.severity),
                start_date=copernicus_event.start_date,
                source_id=copernicus_event.external_id,  # legacy field (EMSR code)
                source_url=copernicus_event.url,
                is_active=True,
                geo_precision=GeoPrecision.approximate,
                geo_method=GeoMethod.source_provided,
            )

            # Create event source link
            await self.event_source_repo.upsert(
                source_id=data_source_id,
                external_id=copernicus_event.external_id,
                event_id=event.id,
                raw_data=copernicus_event.raw_data,
                fetched_at=fetched_at,
            )

            result.created += 1
            logger.debug(f"Created Copernicus event: {copernicus_event.external_id}")

        else:
            # Update existing event source with fresh data
            await self.event_source_repo.upsert(
                source_id=data_source_id,
                external_id=copernicus_event.external_id,
                event_id=existing_event_id,
                raw_data=copernicus_event.raw_data,
                fetched_at=fetched_at,
            )

            # Try to update the event if we have better data
            update_result = await self.event_repo.update_if_better(
                existing_event_id,
                {
                    "title": copernicus_event.title,
                    "description": copernicus_event.description,
                    "lat": copernicus_event.lat,
                    "lng": copernicus_event.lng,
                    "region": copernicus_event.country,
                    "severity": self._map_copernicus_severity(copernicus_event.severity),
                    "source_url": copernicus_event.url,
                    "geo_precision": GeoPrecision.approximate,
                    "geo_method": GeoMethod.source_provided,
                },
            )

            if update_result is not None:
                result.updated += 1
                logger.debug(f"Updated Copernicus event: {copernicus_event.external_id}")
            else:
                # Event source was updated but event data wasn't improved
                result.updated += 1
                logger.debug(f"Refreshed Copernicus event source: {copernicus_event.external_id}")

    def _map_gdacs_event_type(self, event_type: str) -> EventType:
        """Map GDACS event type string to EventType enum.

        Args:
            event_type: Event type string from GDACS (e.g., "earthquake", "flood")

        Returns:
            Corresponding EventType enum value
        """
        return GDACS_EVENT_TYPE_MAP.get(event_type.lower(), EventType.other)

    def _map_gdacs_severity(self, severity: str) -> SeverityLevel:
        """Map GDACS severity string to SeverityLevel enum.

        Args:
            severity: Severity string from GDACS (e.g., "low", "medium", "high")

        Returns:
            Corresponding SeverityLevel enum value
        """
        return GDACS_SEVERITY_MAP.get(severity.lower(), SeverityLevel.medium)

    def _map_copernicus_event_type(self, event_type: str) -> EventType:
        """Map Copernicus event type string to EventType enum.

        Args:
            event_type: Event type string from Copernicus (e.g., "flood", "wildfire")

        Returns:
            Corresponding EventType enum value
        """
        return COPERNICUS_EVENT_TYPE_MAP.get(event_type.lower(), EventType.other)

    def _map_copernicus_severity(self, severity: str) -> SeverityLevel:
        """Map Copernicus severity string to SeverityLevel enum.

        Args:
            severity: Severity string from Copernicus (from calculate_severity)

        Returns:
            Corresponding SeverityLevel enum value
        """
        return COPERNICUS_SEVERITY_MAP.get(severity.lower(), SeverityLevel.medium)
