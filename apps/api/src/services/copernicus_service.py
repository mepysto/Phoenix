import asyncio
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx

from src.core.config import settings
from src.core.exceptions import DataSyncError, ExternalAPIError

logger = logging.getLogger(__name__)

COPERNICUS_EVENT_TYPE_MAP = {
    "flood": "flood",
    "storm": "hurricane",
    "wildfire": "wildfire",
    "earthquake": "earthquake",
    "volcano": "volcano",
    "drought": "drought",
    "landslide": "landslide",
    "tsunami": "tsunami",
    "industrial-accident": "industrial",
    "other": "other",
}

COPERNICUS_SEVERITY_THRESHOLDS = {
    "critical": 10,
    "high": 5,
}

# Retry configuration
DEFAULT_TIMEOUT = 10.0  # seconds
MAX_RETRIES = 3
INITIAL_BACKOFF = 1.0  # seconds
BACKOFF_MULTIPLIER = 2.0
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


@dataclass
class CopernicusEvent:
    external_id: str
    event_type: str
    title: str
    description: str
    lat: float
    lng: float
    country: str
    severity: str
    n_aois: int
    n_products: int
    start_date: datetime
    url: str
    raw_data: dict[str, Any]


def parse_wkt_point(wkt: str) -> tuple[float, float] | None:
    if not wkt:
        return None

    # POINT(lng lat) format - regex needed for WKT parsing
    match = re.match(r"POINT\s*\(\s*([+-]?\d+\.?\d*)\s+([+-]?\d+\.?\d*)\s*\)", wkt, re.IGNORECASE)
    if match:
        lng = float(match.group(1))
        lat = float(match.group(2))
        return (lat, lng)

    return None


def calculate_severity(n_aois: int) -> str:
    if n_aois > COPERNICUS_SEVERITY_THRESHOLDS["critical"]:
        return "critical"
    elif n_aois > COPERNICUS_SEVERITY_THRESHOLDS["high"]:
        return "high"
    else:
        return "medium"


class CopernicusEMSService:
    ACTIVATIONS_URL = "https://mapping.emergency.copernicus.eu/activations/api/activations/"
    RAPID_MAPPING_URL = (
        "https://rapidmapping.emergency.copernicus.eu/backend/dashboard-api/public-activations-info/"
    )

    def __init__(
        self,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = MAX_RETRIES,
    ) -> None:
        self.api_url = settings.copernicus_api_url
        self.timeout = timeout
        self.max_retries = max_retries

    async def _request_with_retry(
        self,
        url: str,
        params: dict[str, str] | None = None,
    ) -> httpx.Response:
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
                                f"Copernicus request failed with status {response.status_code}, "
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
                        f"Copernicus request timeout, retrying in {backoff:.1f}s "
                        f"(attempt {attempt + 1}/{self.max_retries + 1})"
                    )
                    await asyncio.sleep(backoff)
                    backoff *= BACKOFF_MULTIPLIER
                else:
                    logger.error(f"Copernicus request timeout after {self.max_retries + 1} attempts")

            except httpx.ConnectError as e:
                last_exception = e
                if attempt < self.max_retries:
                    logger.warning(
                        f"Copernicus connection error, retrying in {backoff:.1f}s "
                        f"(attempt {attempt + 1}/{self.max_retries + 1})"
                    )
                    await asyncio.sleep(backoff)
                    backoff *= BACKOFF_MULTIPLIER
                else:
                    logger.error(
                        f"Copernicus connection failed after {self.max_retries + 1} attempts: {e}"
                    )

            # Non-retryable HTTP errors
            except httpx.HTTPStatusError as e:
                status_code = e.response.status_code if e.response else None
                raise ExternalAPIError(
                    message=f"HTTP error: {e}",
                    service_name="Copernicus",
                    status_code=status_code,
                    details={"url": url, "params": params},
                ) from e

            except httpx.RequestError as e:
                last_exception = e
                if attempt < self.max_retries:
                    logger.warning(
                        f"Copernicus request error ({type(e).__name__}), retrying in {backoff:.1f}s "
                        f"(attempt {attempt + 1}/{self.max_retries + 1})"
                    )
                    await asyncio.sleep(backoff)
                    backoff *= BACKOFF_MULTIPLIER
                else:
                    logger.error(
                        f"Copernicus request failed after {self.max_retries + 1} attempts: {e}"
                    )

        # All retries exhausted
        raise ExternalAPIError(
            message=f"Request failed after {self.max_retries + 1} attempts",
            service_name="Copernicus",
            details={
                "url": url,
                "params": params,
                "last_error": str(last_exception) if last_exception else None,
            },
        )

    async def fetch_activations(
        self,
        limit: int = 100,
        category: str | None = None,
        ordering: str = "-activationTime",
    ) -> list[CopernicusEvent]:
        params: dict[str, str] = {
            "limit": str(limit),
            "ordering": ordering,
        }

        if category:
            params["category__slug"] = category

        response = await self._request_with_retry(self.ACTIVATIONS_URL, params=params)
        data = response.json()

        events: list[CopernicusEvent] = []
        results = data.get("results", [])

        for item in results:
            try:
                event = self._parse_activation(item)
                if event:
                    events.append(event)
            except Exception as e:
                logger.warning(f"Failed to parse Copernicus activation: {e}")
                continue

        logger.info(f"Fetched {len(events)} Copernicus activations")
        return events

    def _parse_activation(self, item: dict[str, Any]) -> CopernicusEvent | None:
        code = item.get("code", "")
        if not code:
            return None

        name = item.get("name", "")

        category_data = item.get("category", {})
        category_slug = category_data.get("slug", "other") if category_data else "other"
        event_type = COPERNICUS_EVENT_TYPE_MAP.get(category_slug, "other")

        centroid_wkt = item.get("centroid", "")
        coords = parse_wkt_point(centroid_wkt)
        if not coords:
            logger.debug(f"Skipping activation {code}: no valid centroid")
            return None

        lat, lng = coords

        countries = item.get("countries", [])
        country = ""
        if countries and len(countries) > 0:
            country = countries[0].get("name", "") or countries[0].get("short_name", "")

        n_aois = item.get("n_aois", 0) or 0
        n_products = item.get("n_products", 0) or 0

        severity = calculate_severity(n_aois)

        activation_time_str = item.get("activationTime", "")
        start_date = datetime.now(timezone.utc)
        if activation_time_str:
            try:
                start_date = datetime.fromisoformat(activation_time_str.replace("Z", "+00:00"))
            except ValueError:
                pass

        url = f"https://rapidmapping.emergency.copernicus.eu/EMSR/{code}"

        drm_phase = item.get("drmPhase", "")
        description = f"{category_data.get('name', 'Event')} in {country}"
        if drm_phase:
            description += f" ({drm_phase} phase)"
        if n_aois > 0:
            description += f" - {n_aois} areas of interest"

        raw_data = {
            "code": code,
            "category": category_data,
            "centroid": centroid_wkt,
            "countries": countries,
            "n_aois": n_aois,
            "n_products": n_products,
            "drmPhase": drm_phase,
            "activationTime": activation_time_str,
        }

        return CopernicusEvent(
            external_id=code,
            event_type=event_type,
            title=name,
            description=description,
            lat=lat,
            lng=lng,
            country=country,
            severity=severity,
            n_aois=n_aois,
            n_products=n_products,
            start_date=start_date,
            url=url,
            raw_data=raw_data,
        )

    async def fetch_activation_details(self, code: str) -> dict[str, Any] | None:
        params = {"code": code}

        try:
            response = await self._request_with_retry(self.RAPID_MAPPING_URL, params=params)
            data = response.json()

            if isinstance(data, list) and len(data) > 0:
                return data[0]
            elif isinstance(data, dict):
                return data

            return None

        except ExternalAPIError as e:
            if e.status_code == 404:
                logger.info(f"Activation {code} not found in Rapid Mapping")
                return None
            raise

    async def fetch_activations_by_category(
        self,
        categories: list[str] | None = None,
        limit_per_category: int = 50,
    ) -> list[CopernicusEvent]:
        if categories is None:
            return await self.fetch_activations(limit=limit_per_category * 4)

        all_events: list[CopernicusEvent] = []
        seen_codes: set[str] = set()

        for category in categories:
            events = await self.fetch_activations(
                limit=limit_per_category,
                category=category,
            )

            for event in events:
                if event.external_id not in seen_codes:
                    all_events.append(event)
                    seen_codes.add(event.external_id)

        logger.info(f"Fetched {len(all_events)} unique Copernicus activations across categories")
        return all_events

    async def sync_events(self) -> int:
        try:
            events = await self.fetch_activations(limit=100)
            return len(events)
        except ExternalAPIError as e:
            raise DataSyncError(
                message=f"Failed to sync events: {e.message}",
                source="Copernicus",
                retry_count=self.max_retries,
                details=e.details,
            ) from e
