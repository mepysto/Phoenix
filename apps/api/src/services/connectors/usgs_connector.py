"""USGS Earthquake API Connector.

This module implements a connector for the USGS Earthquake Hazards Program
GeoJSON feed. The USGS provides real-time earthquake data globally with
various magnitude thresholds and time windows.

API Documentation: https://earthquake.usgs.gov/earthquakes/feed/v1.0/geojson.php

Example:
    connector = USGSConnector(feed="4.5_week")
    events = await connector.fetch_events()
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx

from src.core.exceptions import ExternalAPIError
from src.services.connectors.base import RawEvent

logger = logging.getLogger(__name__)

# Feed configuration
# Each feed provides earthquakes filtered by magnitude and time window
USGS_FEEDS = {
    "4.5_day": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/4.5_day.geojson",
    "4.5_week": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/4.5_week.geojson",
    "all_day": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson",
    "significant_month": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/significant_month.geojson",
}

# Retry configuration (consistent with other connectors)
DEFAULT_TIMEOUT = 30.0
MAX_RETRIES = 3
INITIAL_BACKOFF = 1.0
BACKOFF_MULTIPLIER = 2.0
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


@dataclass
class USGSEarthquake:
    """USGS earthquake event data.
    
    Represents a single earthquake event from the USGS GeoJSON feed.
    
    Attributes:
        event_id: Unique USGS event identifier (e.g., "us7000rlps")
        title: Event title (e.g., "M 4.4 - 161 km NNW of Tobelo, Indonesia")
        place: Human-readable location description
        magnitude: Earthquake magnitude value
        mag_type: Magnitude type (e.g., "mb", "mw", "ml")
        latitude: Event latitude in degrees
        longitude: Event longitude in degrees
        depth_km: Depth of the earthquake in kilometers
        time: Event timestamp (UTC)
        url: URL to the USGS event page
        alert: PAGER alert level ("green", "yellow", "orange", "red", or None)
        tsunami: Whether a tsunami warning was issued
        raw_data: Complete original GeoJSON feature
    """
    event_id: str
    title: str
    place: str
    magnitude: float
    mag_type: str
    latitude: float
    longitude: float
    depth_km: float
    time: datetime
    url: str
    alert: str | None  # "green", "yellow", "orange", "red", None
    tsunami: bool
    raw_data: dict[str, Any]


class USGSConnector:
    """USGS Earthquake API Connector.
    
    Fetches earthquake data from the USGS Earthquake Hazards Program
    GeoJSON feeds. Implements the Connector protocol for integration
    with the Phoenix ingestion pipeline.
    
    The USGS API is free, requires no authentication, and has no rate limits.
    Data is updated every minute.
    
    Attributes:
        source_name: Identifier for this data source ("USGS")
    
    Example:
        # Fetch significant earthquakes from the past week
        connector = USGSConnector(feed="4.5_week")
        raw_events = await connector.fetch_events()
        
        # Fetch all earthquakes from the past day
        connector = USGSConnector(feed="all_day")
        earthquakes = await connector.fetch_earthquakes()
    """
    
    source_name: str = "USGS"
    
    def __init__(
        self,
        feed: str = "4.5_week",
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = MAX_RETRIES,
    ) -> None:
        """Initialize the USGS connector.
        
        Args:
            feed: Feed identifier. One of:
                - "4.5_day": M4.5+ earthquakes, past day
                - "4.5_week": M4.5+ earthquakes, past week (default)
                - "all_day": All earthquakes, past day
                - "significant_month": Significant earthquakes, past month
            timeout: HTTP request timeout in seconds
            max_retries: Maximum number of retry attempts
            
        Raises:
            ValueError: If feed is not a valid feed identifier
        """
        if feed not in USGS_FEEDS:
            raise ValueError(
                f"Unknown feed: {feed}. Available feeds: {list(USGS_FEEDS.keys())}"
            )
        self.feed = feed
        self.feed_url = USGS_FEEDS[feed]
        self.timeout = timeout
        self.max_retries = max_retries
    
    async def _request_with_retry(self, url: str) -> dict[str, Any]:
        """Make HTTP GET request with exponential backoff retry.
        
        Args:
            url: The URL to request
            
        Returns:
            Parsed JSON response as a dictionary
            
        Raises:
            ExternalAPIError: When all retry attempts fail
        """
        last_exception: Exception | None = None
        backoff = INITIAL_BACKOFF
        
        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.get(url)
                    
                    # Check for retryable status codes
                    if response.status_code in RETRYABLE_STATUS_CODES:
                        if attempt < self.max_retries:
                            logger.warning(
                                f"USGS request failed with status {response.status_code}, "
                                f"retrying in {backoff:.1f}s (attempt {attempt + 1}/{self.max_retries + 1})"
                            )
                            await asyncio.sleep(backoff)
                            backoff *= BACKOFF_MULTIPLIER
                            continue
                    
                    response.raise_for_status()
                    return response.json()
                    
            except httpx.TimeoutException as e:
                last_exception = e
                if attempt < self.max_retries:
                    logger.warning(
                        f"USGS request timeout, retrying in {backoff:.1f}s "
                        f"(attempt {attempt + 1}/{self.max_retries + 1})"
                    )
                    await asyncio.sleep(backoff)
                    backoff *= BACKOFF_MULTIPLIER
                else:
                    logger.error(f"USGS request timeout after {self.max_retries + 1} attempts")
                    
            except httpx.ConnectError as e:
                last_exception = e
                if attempt < self.max_retries:
                    logger.warning(
                        f"USGS connection error, retrying in {backoff:.1f}s "
                        f"(attempt {attempt + 1}/{self.max_retries + 1})"
                    )
                    await asyncio.sleep(backoff)
                    backoff *= BACKOFF_MULTIPLIER
                else:
                    logger.error(
                        f"USGS connection failed after {self.max_retries + 1} attempts: {e}"
                    )
                    
            except httpx.HTTPStatusError as e:
                # Non-retryable HTTP errors
                status_code = e.response.status_code if e.response else None
                raise ExternalAPIError(
                    message=f"HTTP error: {e}",
                    service_name="USGS",
                    status_code=status_code,
                    details={"url": url},
                ) from e
                
            except httpx.RequestError as e:
                last_exception = e
                if attempt < self.max_retries:
                    logger.warning(
                        f"USGS request error ({type(e).__name__}), retrying in {backoff:.1f}s "
                        f"(attempt {attempt + 1}/{self.max_retries + 1})"
                    )
                    await asyncio.sleep(backoff)
                    backoff *= BACKOFF_MULTIPLIER
                else:
                    logger.error(
                        f"USGS request failed after {self.max_retries + 1} attempts: {e}"
                    )
        
        # All retries exhausted
        raise ExternalAPIError(
            message=f"Request failed after {self.max_retries + 1} attempts",
            service_name="USGS",
            details={
                "url": url,
                "last_error": str(last_exception) if last_exception else None,
            },
        )
    
    def _parse_feature(self, feature: dict[str, Any]) -> USGSEarthquake | None:
        """Parse a single GeoJSON feature into USGSEarthquake.
        
        Args:
            feature: A GeoJSON feature object from the USGS feed
            
        Returns:
            USGSEarthquake instance, or None if the feature is invalid
        """
        props = feature.get("properties", {})
        geometry = feature.get("geometry", {})
        coords = geometry.get("coordinates", [])
        
        # Coordinates are [longitude, latitude, depth]
        if len(coords) < 2:
            logger.debug(f"Skipping feature with missing coordinates: {feature.get('id')}")
            return None
        
        event_id = feature.get("id", "")
        if not event_id:
            logger.debug("Skipping feature with missing event ID")
            return None
        
        # Parse timestamp (USGS provides milliseconds since epoch)
        time_ms = props.get("time")
        if time_ms is not None:
            try:
                event_time = datetime.fromtimestamp(time_ms / 1000, tz=timezone.utc)
            except (ValueError, OSError) as e:
                logger.warning(f"Invalid timestamp {time_ms} for event {event_id}: {e}")
                event_time = datetime.now(timezone.utc)
        else:
            event_time = datetime.now(timezone.utc)
        
        # Extract magnitude, defaulting to 0 if not present
        magnitude = props.get("mag")
        if magnitude is None:
            magnitude = 0.0
        else:
            try:
                magnitude = float(magnitude)
            except (ValueError, TypeError):
                magnitude = 0.0
        
        return USGSEarthquake(
            event_id=event_id,
            title=props.get("title", f"Earthquake {event_id}"),
            place=props.get("place") or "Unknown location",
            magnitude=magnitude,
            mag_type=props.get("magType") or "",
            longitude=float(coords[0]),
            latitude=float(coords[1]),
            depth_km=float(coords[2]) if len(coords) > 2 else 0.0,
            time=event_time,
            url=props.get("url") or "",
            alert=props.get("alert"),  # Can be None, "green", "yellow", "orange", "red"
            tsunami=bool(props.get("tsunami", 0)),
            raw_data=feature,
        )
    
    async def fetch_earthquakes(self) -> list[USGSEarthquake]:
        """Fetch and parse earthquakes from USGS GeoJSON feed.
        
        Returns:
            List of USGSEarthquake instances
            
        Raises:
            ExternalAPIError: When the API request fails
        """
        logger.info(f"Fetching earthquakes from USGS feed: {self.feed}")
        data = await self._request_with_retry(self.feed_url)
        
        earthquakes: list[USGSEarthquake] = []
        features = data.get("features", [])
        
        for feature in features:
            try:
                eq = self._parse_feature(feature)
                if eq:
                    earthquakes.append(eq)
            except Exception as e:
                logger.warning(f"Failed to parse USGS feature: {e}")
                continue
        
        logger.info(f"Fetched {len(earthquakes)} earthquakes from USGS ({self.feed})")
        return earthquakes
    
    async def fetch_events(self) -> list[RawEvent]:
        """Fetch events and convert to RawEvent format.
        
        This method implements the Connector protocol, returning events
        in the normalized RawEvent format for the ingestion pipeline.
        
        Returns:
            List of RawEvent instances
            
        Raises:
            ExternalAPIError: When the API request fails
        """
        earthquakes = await self.fetch_earthquakes()
        
        return [
            RawEvent(
                source_name=self.source_name,
                external_id=eq.event_id,
                title=eq.title,
                description=self._build_description(eq),
                start_date=eq.time,
                source_url=eq.url,
                lat=eq.latitude,
                lng=eq.longitude,
                event_type_raw="earthquake",
                severity_raw=eq.alert,  # USGS PAGER alert level
                magnitude=eq.magnitude,
                raw_data=eq.raw_data,
            )
            for eq in earthquakes
        ]
    
    def _build_description(self, eq: USGSEarthquake) -> str:
        """Build a human-readable description for an earthquake.
        
        Args:
            eq: USGSEarthquake instance
            
        Returns:
            Formatted description string
        """
        parts = [f"Magnitude {eq.magnitude}"]
        
        if eq.mag_type:
            parts[0] += f" {eq.mag_type}"
        
        parts[0] += " earthquake"
        
        if eq.depth_km > 0:
            parts.append(f"Depth: {eq.depth_km:.1f} km")
        
        if eq.place and eq.place != "Unknown location":
            parts.append(f"Location: {eq.place}")
        
        if eq.tsunami:
            parts.append("Tsunami warning issued")
        
        return ". ".join(parts) + "."
