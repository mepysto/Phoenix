"""Base classes for external data source connectors.

This module defines the RawEvent dataclass and Connector protocol that all
external data source connectors must implement.

Example:
    class EONETConnector:
        source_name = "EONET"
        
        async def fetch_events(self) -> list[RawEvent]:
            # Fetch from NASA EONET API
            ...
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class RawEvent:
    """Raw event data parsed from an external source.
    
    This dataclass represents the minimal normalized structure for events
    coming from any external source (GDACS, USGS, EONET, ReliefWeb, etc.).
    
    The data here is "raw" in the sense that it hasn't been fully normalized
    to our internal Event model - type mappings, severity calculations, and
    admin area resolution happen in the Normalizer stage.
    
    Attributes:
        source_name: Name of the data source (e.g., "GDACS", "USGS", "EONET")
        external_id: Unique identifier within the source
        title: Event title/headline
        description: Detailed description (optional)
        start_date: When the event started
        end_date: When the event ended (optional, None if ongoing)
        source_url: URL to the original event page (optional)
        lat: Latitude coordinate (optional, may not be available)
        lng: Longitude coordinate (optional, may not be available)
        country: Country name where event occurred (optional)
        country_code: ISO alpha-2 or alpha-3 country code (optional)
        event_type_raw: Source's original event type string
        severity_raw: Source's original severity string
        magnitude: Numeric magnitude (e.g., USGS earthquake magnitude)
        glide_number: ReliefWeb GLIDE number for disaster tracking
        raw_data: Complete original data from the source
    """
    
    # Required identifiers
    source_name: str
    external_id: str
    title: str
    start_date: datetime
    
    # Optional basic info
    description: str | None = None
    end_date: datetime | None = None
    source_url: str | None = None
    
    # Coordinates (may be absent for some sources)
    lat: float | None = None
    lng: float | None = None
    
    # Country info (for admin_area resolution when no coordinates)
    country: str | None = None
    country_code: str | None = None
    
    # Source-specific data for normalization
    event_type_raw: str | None = None
    severity_raw: str | None = None
    magnitude: float | None = None
    glide_number: str | None = None
    
    # Full original data for reference/debugging
    raw_data: dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self) -> None:
        """Validate required fields."""
        if not self.source_name:
            raise ValueError("source_name is required")
        if not self.external_id:
            raise ValueError("external_id is required")
        if not self.title:
            raise ValueError("title is required")


@runtime_checkable
class Connector(Protocol):
    """Protocol for external API connectors.
    
    All data source connectors must implement this protocol to ensure
    consistent interface for fetching events.
    
    The connector is responsible for:
    1. Making HTTP requests to the external API
    2. Parsing the response format (XML, JSON, etc.)
    3. Converting to RawEvent dataclass instances
    
    Attributes:
        source_name: Identifier for the data source (e.g., "GDACS", "EONET")
    
    Example:
        class USGSConnector:
            source_name = "USGS"
            
            async def fetch_events(self) -> list[RawEvent]:
                response = await self._fetch_geojson()
                return [self._parse_feature(f) for f in response["features"]]
    """
    
    source_name: str
    
    async def fetch_events(self) -> list[RawEvent]:
        """Fetch events from the external API.
        
        Returns:
            List of RawEvent instances parsed from the API response.
            
        Raises:
            ExternalAPIError: When the API request fails
        """
        ...
