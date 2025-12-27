import asyncio
import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx

from src.core.config import settings
from src.core.exceptions import DataSyncError, ExternalAPIError

logger = logging.getLogger(__name__)

GDACS_EVENT_TYPE_MAP = {
    "EQ": "earthquake",
    "FL": "flood",
    "TC": "hurricane",
    "VO": "volcano",
    "DR": "drought",
    "WF": "wildfire",
    "TS": "tsunami",
}

GDACS_SEVERITY_MAP = {
    "Green": "low",
    "Orange": "medium",
    "Red": "high",
}

# Retry configuration
DEFAULT_TIMEOUT = 10.0  # seconds
MAX_RETRIES = 3
INITIAL_BACKOFF = 1.0  # seconds
BACKOFF_MULTIPLIER = 2.0
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


@dataclass
class GDACSEvent:
    external_id: str
    event_type: str
    title: str
    description: str
    lat: float
    lng: float
    country: str
    severity: str
    population: int | None
    start_date: datetime
    url: str
    raw_data: dict[str, Any]


class GDACSService:
    RSS_URL = "https://www.gdacs.org/xml/rss.xml"
    API_URL = "https://www.gdacs.org/gdacsapi/api"

    def __init__(
        self,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = MAX_RETRIES,
    ) -> None:
        self.api_url = settings.gdacs_api_url
        self.timeout = timeout
        self.max_retries = max_retries

    async def _request_with_retry(
        self,
        url: str,
        params: dict[str, str] | None = None,
    ) -> httpx.Response:
        """
        Make an HTTP GET request with exponential backoff retry.

        Args:
            url: The URL to request
            params: Optional query parameters

        Returns:
            httpx.Response on success

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
                                f"GDACS request failed with status {response.status_code}, "
                                f"retrying in {backoff:.1f}s (attempt {attempt + 1}/{self.max_retries + 1})"
                            )
                            await asyncio.sleep(backoff)
                            backoff *= BACKOFF_MULTIPLIER
                            continue

                    response.raise_for_status()
                    return response

            except httpx.TimeoutException as e:
                last_exception = e
                if attempt < self.max_retries:
                    logger.warning(
                        f"GDACS request timeout, retrying in {backoff:.1f}s "
                        f"(attempt {attempt + 1}/{self.max_retries + 1})"
                    )
                    await asyncio.sleep(backoff)
                    backoff *= BACKOFF_MULTIPLIER
                else:
                    logger.error(f"GDACS request timeout after {self.max_retries + 1} attempts")

            except httpx.ConnectError as e:
                last_exception = e
                if attempt < self.max_retries:
                    logger.warning(
                        f"GDACS connection error, retrying in {backoff:.1f}s "
                        f"(attempt {attempt + 1}/{self.max_retries + 1})"
                    )
                    await asyncio.sleep(backoff)
                    backoff *= BACKOFF_MULTIPLIER
                else:
                    logger.error(
                        f"GDACS connection failed after {self.max_retries + 1} attempts: {e}"
                    )

            except httpx.HTTPStatusError as e:
                # Non-retryable HTTP errors
                status_code = e.response.status_code if e.response else None
                raise ExternalAPIError(
                    message=f"HTTP error: {e}",
                    service_name="GDACS",
                    status_code=status_code,
                    details={"url": url, "params": params},
                ) from e

            except httpx.RequestError as e:
                last_exception = e
                if attempt < self.max_retries:
                    logger.warning(
                        f"GDACS request error ({type(e).__name__}), retrying in {backoff:.1f}s "
                        f"(attempt {attempt + 1}/{self.max_retries + 1})"
                    )
                    await asyncio.sleep(backoff)
                    backoff *= BACKOFF_MULTIPLIER
                else:
                    logger.error(
                        f"GDACS request failed after {self.max_retries + 1} attempts: {e}"
                    )

        # All retries exhausted
        raise ExternalAPIError(
            message=f"Request failed after {self.max_retries + 1} attempts",
            service_name="GDACS",
            details={
                "url": url,
                "params": params,
                "last_error": str(last_exception) if last_exception else None,
            },
        )

    async def fetch_rss_events(self) -> list[GDACSEvent]:
        """
        Fetch and parse GDACS RSS feed with retry logic.

        Returns:
            List of parsed GDACS events

        Raises:
            ExternalAPIError: When the request fails after all retries
        """
        response = await self._request_with_retry(self.RSS_URL)
        return self._parse_rss(response.text)

    def _parse_rss(self, xml_content: str) -> list[GDACSEvent]:
        events: list[GDACSEvent] = []
        root = ET.fromstring(xml_content)

        ns = {
            "gdacs": "http://www.gdacs.org",
            "geo": "http://www.w3.org/2003/01/geo/wgs84_pos#",
            "dc": "http://purl.org/dc/elements/1.1/",
        }

        for item in root.findall(".//item"):
            try:
                event = self._parse_item(item, ns)
                if event:
                    events.append(event)
            except Exception:
                continue

        return events

    def _parse_item(self, item: ET.Element, ns: dict[str, str]) -> GDACSEvent | None:
        title = item.findtext("title", "")
        description = item.findtext("description", "")
        link = item.findtext("link", "")

        event_type_code = item.findtext("gdacs:eventtype", "", ns)
        event_type = GDACS_EVENT_TYPE_MAP.get(event_type_code, "other")

        alert_level = item.findtext("gdacs:alertlevel", "Green", ns)
        severity = GDACS_SEVERITY_MAP.get(alert_level, "medium")

        lat_str = item.findtext("geo:lat", "", ns) or item.findtext(
            "{http://www.georss.org/georss}point", ""
        )
        lng_str = item.findtext("geo:long", "", ns)

        if not lat_str:
            georss_point = item.findtext("{http://www.georss.org/georss}point", "")
            if georss_point:
                parts = georss_point.strip().split()
                if len(parts) >= 2:
                    lat_str = parts[0]
                    lng_str = parts[1]

        if not lat_str or not lng_str:
            return None

        lat = float(lat_str)
        lng = float(lng_str)

        country = item.findtext("gdacs:country", "", ns) or ""
        population_str = item.findtext("gdacs:population", "", ns) or ""
        population = int(population_str.replace(" ", "").replace(",", "")) if population_str else None

        event_id = item.findtext("gdacs:eventid", "", ns) or link.split("/")[-1] if link else ""

        pub_date_str = item.findtext("pubDate", "")
        from_date_str = item.findtext("gdacs:fromdate", "", ns)

        start_date = datetime.now(timezone.utc)
        if from_date_str:
            try:
                start_date = datetime.fromisoformat(from_date_str.replace("Z", "+00:00"))
            except ValueError:
                pass
        elif pub_date_str:
            try:
                from email.utils import parsedate_to_datetime
                start_date = parsedate_to_datetime(pub_date_str)
            except Exception:
                pass

        raw_data = {
            "event_type_code": event_type_code,
            "alert_level": alert_level,
            "severity_value": item.findtext("gdacs:severity", "", ns),
            "episode_id": item.findtext("gdacs:episodeid", "", ns),
            "duration": item.findtext("gdacs:duration", "", ns),
            "link": link,
        }

        return GDACSEvent(
            external_id=event_id,
            event_type=event_type,
            title=title,
            description=description,
            lat=lat,
            lng=lng,
            country=country,
            severity=severity,
            population=population,
            start_date=start_date,
            url=link,
            raw_data=raw_data,
        )

    async def fetch_api_events(
        self,
        event_types: list[str] | None = None,
        from_date: str | None = None,
        alert_level: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Fetch events from GDACS API with retry logic.

        Args:
            event_types: Optional list of event type codes to filter
            from_date: Optional start date filter
            alert_level: Optional alert level filter

        Returns:
            List of event features from the API

        Raises:
            ExternalAPIError: When the request fails after all retries
        """
        params: dict[str, str] = {}
        if event_types:
            params["eventlist"] = ",".join(event_types)
        if from_date:
            params["fromdate"] = from_date
        if alert_level:
            params["alertlevel"] = alert_level

        response = await self._request_with_retry(
            f"{self.API_URL}/events/geteventlist/SEARCH",
            params=params,
        )
        return response.json().get("features", [])

    async def sync_events(self) -> int:
        """
        Synchronize events from GDACS RSS feed.

        Returns:
            Number of events fetched

        Raises:
            DataSyncError: When sync fails after all retries
        """
        try:
            events = await self.fetch_rss_events()
            return len(events)
        except ExternalAPIError as e:
            raise DataSyncError(
                message=f"Failed to sync events: {e.message}",
                source="GDACS",
                retry_count=self.max_retries,
                details=e.details,
            ) from e
