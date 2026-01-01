"""Base classes for event normalization.

This module defines the EventUpsertPayload dataclass and Normalizer protocol
for converting RawEvents into database-ready payloads.

Example:
    class EONETNormalizer:
        async def normalize(self, raw: RawEvent) -> EventUpsertPayload:
            severity = self._compute_severity(raw)
            admin_area_id = await self._resolve_admin_area(raw)
            ...
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable
from uuid import UUID

from src.models.event import EventType, GeoMethod, GeoPrecision, SeverityLevel

if TYPE_CHECKING:
    from src.services.connectors.base import RawEvent


@dataclass
class EventUpsertPayload:
    """Normalized event payload ready for database upsert.
    
    This dataclass contains all the fields needed to create or update
    an Event and its associated EventSource in the database.
    
    The normalization process converts source-specific data (RawEvent)
    into this standardized format with:
    - Mapped event types (source type -> EventType enum)
    - Calculated severity (using source-specific strategies)
    - Resolved admin areas (from coordinates or country info)
    - Determined geo precision and method
    
    Attributes:
        type: Normalized event type
        title: Event title
        description: Event description (optional)
        severity: Calculated severity level
        latitude: Event latitude (may be centroid if no exact location)
        longitude: Event longitude (may be centroid if no exact location)
        geo_precision: How precise the coordinates are
        geo_method: How the coordinates were obtained
        admin_area_id: UUID of linked admin area (optional)
        country_code: ISO country code (optional)
        region: Region/country name (optional)
        start_date: Event start datetime
        end_date: Event end datetime (optional)
        is_active: Whether event is currently active
        glide_number: GLIDE disaster identifier (optional)
        source_url: URL to original source (optional)
        source_name: Name of the data source
        external_id: ID within the source
        raw_data: Original raw data for reference
    """
    
    # Event table fields
    type: EventType
    title: str
    severity: SeverityLevel
    start_date: datetime
    source_name: str
    external_id: str
    
    # Optional event fields
    description: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    geo_precision: GeoPrecision = GeoPrecision.unknown
    geo_method: GeoMethod = GeoMethod.source_provided
    admin_area_id: UUID | None = None
    country_code: str | None = None
    region: str | None = None
    end_date: datetime | None = None
    is_active: bool = True
    glide_number: str | None = None
    source_url: str | None = None
    
    # EventSource table fields
    raw_data: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class Normalizer(Protocol):
    """Protocol for event normalizers.
    
    Normalizers convert RawEvent instances from connectors into
    EventUpsertPayload instances ready for database operations.
    
    A normalizer is responsible for:
    1. Mapping source event types to EventType enum
    2. Computing severity using source-specific strategies
    3. Resolving admin areas from coordinates or country info
    4. Determining geo precision and method
    
    Example:
        class USGSNormalizer:
            async def normalize(self, raw: RawEvent) -> EventUpsertPayload:
                return EventUpsertPayload(
                    type=EventType.earthquake,
                    title=raw.title,
                    severity=self._compute_severity(raw.magnitude),
                    ...
                )
    """
    
    async def normalize(self, raw: "RawEvent") -> EventUpsertPayload:
        """Normalize a raw event into an upsert payload.
        
        Args:
            raw: RawEvent from a connector
            
        Returns:
            EventUpsertPayload ready for database operations
        """
        ...
