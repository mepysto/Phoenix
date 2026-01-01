"""NASA EONET (Earth Observatory Natural Event Tracker) API Connector.

This module implements a connector for the NASA EONET API v3.
EONET provides near real-time information about natural events
including wildfires, volcanic eruptions, severe storms, and more.

API Documentation: https://eonet.gsfc.nasa.gov/docs/v3

Example:
    connector = EONETConnector(status="open", days=30)
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

# API configuration
BASE_URL = "https://eonet.gsfc.nasa.gov/api/v3"

# Category mapping from EONET categories to Phoenix EventType
EONET_CATEGORY_MAP = {
    "drought": "drought",
    "earthquakes": "earthquake",
    "floods": "flood",
    "landslides": "landslide",
    "manmade": "industrial",
    "severeStorms": "storm",
    "snow": "other",
    "tempExtremes": "heatwave",  # Note: could also be coldwave based on context
    "volcanoes": "volcano",
    "wildfires": "wildfire",
    "dustHaze": "pollution",
    "seaLakeIce": "other",
    "waterColor": "pollution",
}

# Retry configuration (consistent with other connectors)
DEFAULT_TIMEOUT = 30.0
MAX_RETRIES = 3
INITIAL_BACKOFF = 1.0
BACKOFF_MULTIPLIER = 2.0
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


@dataclass
class EONETEvent:
    """EONET natural event data.

    Represents a single natural event from the NASA EONET API.

    Attributes:
        event_id: Unique EONET event identifier (e.g., "EONET_6789")
        title: Event title (e.g., "Wildfire - California, United States")
        description: Detailed description (optional)
        link: URL to the EONET event page
        closed: When the event closed (None if ongoing)
        categories: List of category IDs (e.g., ["wildfires"])
        sources: List of source dictionaries with "id" and "url"
        latitude: Event latitude in degrees
        longitude: Event longitude in degrees
        geometry_date: Timestamp of the geometry data point
        raw_data: Complete original GeoJSON feature
    """

    event_id: str
    title: str
    description: str | None
    link: str
    closed: datetime | None  # None = ongoing event
    categories: list[str]
    sources: list[dict[str, str]]
    latitude: float
    longitude: float
    geometry_date: datetime
    raw_data: dict[str, Any]


class EONETConnector:
    """NASA EONET API Connector.

    Fetches natural event data from NASA's Earth Observatory Natural
    Event Tracker (EONET) API v3. Implements the Connector protocol
    for integration with the Phoenix ingestion pipeline.

    The EONET API is free, requires no authentication, and has no rate limits.
    Data includes wildfires, volcanoes, severe storms, and other natural events.

    Attributes:
        source_name: Identifier for this data source ("EONET")

    Example:
        # Fetch open events from the past 30 days
        connector = EONETConnector(status="open", days=30)
        raw_events = await connector.fetch_events()

        # Fetch only wildfire events
        connector = EONETConnector(categories=["wildfires"])
        eonet_events = await connector.fetch_eonet_events()
    """

    source_name: str = "EONET"

    def __init__(
        self,
        status: str = "open",
        days: int = 30,
        categories: list[str] | None = None,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = MAX_RETRIES,
    ) -> None:
        """Initialize the EONET connector.

        Args:
            status: Event status filter. One of:
                - "open": Only ongoing events (default)
                - "closed": Only closed/ended events
                - "all": Both open and closed events
            days: Fetch events from the last N days (default: 30)
            categories: List of category IDs to filter by (optional).
                Available: drought, earthquakes, floods, landslides,
                manmade, severeStorms, snow, tempExtremes, volcanoes,
                wildfires, dustHaze, seaLakeIce, waterColor
            timeout: HTTP request timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        self.status = status
        self.days = days
        self.categories = categories
        self.timeout = timeout
        self.max_retries = max_retries

    async def _request_with_retry(
        self, url: str, params: dict[str, str] | None = None
    ) -> dict[str, Any]:
        """Make HTTP GET request with exponential backoff retry.

        Args:
            url: The URL to request
            params: Optional query parameters

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
                    response = await client.get(url, params=params)

                    # Check for retryable status codes
                    if response.status_code in RETRYABLE_STATUS_CODES:
                        if attempt < self.max_retries:
                            logger.warning(
                                f"EONET request failed with status {response.status_code}, "
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
                        f"EONET request timeout, retrying in {backoff:.1f}s "
                        f"(attempt {attempt + 1}/{self.max_retries + 1})"
                    )
                    await asyncio.sleep(backoff)
                    backoff *= BACKOFF_MULTIPLIER
                else:
                    logger.error(
                        f"EONET request timeout after {self.max_retries + 1} attempts"
                    )

            except httpx.ConnectError as e:
                last_exception = e
                if attempt < self.max_retries:
                    logger.warning(
                        f"EONET connection error, retrying in {backoff:.1f}s "
                        f"(attempt {attempt + 1}/{self.max_retries + 1})"
                    )
                    await asyncio.sleep(backoff)
                    backoff *= BACKOFF_MULTIPLIER
                else:
                    logger.error(
                        f"EONET connection failed after {self.max_retries + 1} attempts: {e}"
                    )

            except httpx.HTTPStatusError as e:
                # Non-retryable HTTP errors
                status_code = e.response.status_code if e.response else None
                raise ExternalAPIError(
                    message=f"HTTP error: {e}",
                    service_name="EONET",
                    status_code=status_code,
                    details={"url": url, "params": params},
                ) from e

            except httpx.RequestError as e:
                last_exception = e
                if attempt < self.max_retries:
                    logger.warning(
                        f"EONET request error ({type(e).__name__}), retrying in {backoff:.1f}s "
                        f"(attempt {attempt + 1}/{self.max_retries + 1})"
                    )
                    await asyncio.sleep(backoff)
                    backoff *= BACKOFF_MULTIPLIER
                else:
                    logger.error(
                        f"EONET request failed after {self.max_retries + 1} attempts: {e}"
                    )

        # All retries exhausted
        raise ExternalAPIError(
            message=f"Request failed after {self.max_retries + 1} attempts",
            service_name="EONET",
            details={
                "url": url,
                "params": params,
                "last_error": str(last_exception) if last_exception else None,
            },
        )

    def _extract_coordinates(
        self, geometry: dict[str, Any]
    ) -> tuple[float, float] | None:
        """Extract representative coordinates from GeoJSON geometry.

        Handles Point, MultiPoint, and Polygon geometry types by
        extracting a single representative coordinate pair.

        Args:
            geometry: GeoJSON geometry object

        Returns:
            Tuple of (latitude, longitude) or None if extraction fails
        """
        geom_type = geometry.get("type", "")
        coords = geometry.get("coordinates", [])

        if not coords:
            return None

        if geom_type == "Point" and len(coords) >= 2:
            # Point: [longitude, latitude]
            return (coords[1], coords[0])

        elif geom_type == "MultiPoint" and coords:
            # MultiPoint: [[lon, lat], [lon, lat], ...]
            # Use the first point
            if len(coords[0]) >= 2:
                return (coords[0][1], coords[0][0])

        elif geom_type == "Polygon" and coords:
            # Polygon: [[[lon, lat], [lon, lat], ...]]
            # Use the first point of the first (outer) ring
            outer_ring = coords[0]
            if outer_ring and len(outer_ring[0]) >= 2:
                return (outer_ring[0][1], outer_ring[0][0])

        elif geom_type == "LineString" and coords:
            # LineString: [[lon, lat], [lon, lat], ...]
            # Use the first point
            if len(coords[0]) >= 2:
                return (coords[0][1], coords[0][0])

        return None

    def _parse_feature(self, feature: dict[str, Any]) -> EONETEvent | None:
        """Parse a single GeoJSON feature into EONETEvent.

        Args:
            feature: A GeoJSON feature object from the EONET feed

        Returns:
            EONETEvent instance, or None if the feature is invalid
        """
        props = feature.get("properties", {})
        geometry = feature.get("geometry", {})

        # Get event ID from properties or feature
        event_id = props.get("id", feature.get("id", ""))
        if not event_id:
            logger.debug("Skipping feature with missing event ID")
            return None

        # Extract coordinates
        coordinates = self._extract_coordinates(geometry)
        if coordinates is None:
            logger.debug(f"Skipping feature {event_id} with missing/invalid coordinates")
            return None

        latitude, longitude = coordinates

        # Parse categories
        categories = [c.get("id", "") for c in props.get("categories", []) if c.get("id")]

        # Parse sources
        sources = props.get("sources", [])

        # Parse closed date (None if ongoing)
        closed_str = props.get("closed")
        closed: datetime | None = None
        if closed_str:
            try:
                closed = datetime.fromisoformat(closed_str.replace("Z", "+00:00"))
            except ValueError as e:
                logger.warning(f"Invalid closed date {closed_str} for event {event_id}: {e}")

        # Parse geometry date (first geometry date or current time)
        geometry_dates = props.get("geometryDates", [])
        geometry_date = datetime.now(timezone.utc)
        if geometry_dates:
            try:
                geometry_date = datetime.fromisoformat(
                    geometry_dates[0].replace("Z", "+00:00")
                )
            except ValueError as e:
                logger.warning(
                    f"Invalid geometry date {geometry_dates[0]} for event {event_id}: {e}"
                )

        return EONETEvent(
            event_id=event_id,
            title=props.get("title", f"EONET Event {event_id}"),
            description=props.get("description"),
            link=props.get("link", ""),
            closed=closed,
            categories=categories,
            sources=sources,
            latitude=latitude,
            longitude=longitude,
            geometry_date=geometry_date,
            raw_data=feature,
        )

    async def fetch_eonet_events(self) -> list[EONETEvent]:
        """Fetch and parse events from EONET GeoJSON API.

        Returns:
            List of EONETEvent instances

        Raises:
            ExternalAPIError: When the API request fails
        """
        logger.info(
            f"Fetching events from EONET (status={self.status}, days={self.days})"
        )

        url = f"{BASE_URL}/events/geojson"
        params: dict[str, str] = {
            "status": self.status,
            "days": str(self.days),
        }
        if self.categories:
            params["category"] = ",".join(self.categories)

        data = await self._request_with_retry(url, params)

        events: list[EONETEvent] = []
        features = data.get("features", [])

        for feature in features:
            try:
                event = self._parse_feature(feature)
                if event:
                    events.append(event)
            except Exception as e:
                logger.warning(f"Failed to parse EONET feature: {e}")
                continue

        logger.info(f"Fetched {len(events)} events from EONET")
        return events

    async def fetch_events(self) -> list[RawEvent]:
        """Fetch events and convert to RawEvent format.

        This method implements the Connector protocol, returning events
        in the normalized RawEvent format for the ingestion pipeline.

        Returns:
            List of RawEvent instances

        Raises:
            ExternalAPIError: When the API request fails
        """
        eonet_events = await self.fetch_eonet_events()

        raw_events: list[RawEvent] = []
        for event in eonet_events:
            # Map category to EventType
            event_type_raw = event.categories[0] if event.categories else "other"
            mapped_type = EONET_CATEGORY_MAP.get(event_type_raw, "other")

            # Build description
            desc_parts: list[str] = []
            if event.description:
                desc_parts.append(event.description)
            if event.sources:
                source_names = [s.get("id", "Unknown") for s in event.sources]
                desc_parts.append(f"Sources: {', '.join(source_names)}")

            raw_events.append(
                RawEvent(
                    source_name=self.source_name,
                    external_id=event.event_id,
                    title=event.title,
                    description=" | ".join(desc_parts) if desc_parts else None,
                    start_date=event.geometry_date,
                    end_date=event.closed,
                    source_url=event.link,
                    lat=event.latitude,
                    lng=event.longitude,
                    event_type_raw=mapped_type,
                    raw_data=event.raw_data,
                )
            )

        return raw_events
