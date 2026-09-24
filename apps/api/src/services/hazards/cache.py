"""Shared caching for hazard feeds: TTL cache that serves stale data on error."""

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

import httpx

from src.core.exceptions import ExternalAPIError

logger = logging.getLogger(__name__)

# Failures that mean "upstream is unavailable or changed", not a bug
UPSTREAM_ERRORS = (httpx.HTTPError, ValueError, KeyError)


class StaleOnErrorCache:
    """Cache one GeoJSON result for `ttl_seconds`.

    If refreshing fails, the last good result is returned with `stale: True`
    so the map keeps showing something useful. With no cached result the
    failure surfaces as ExternalAPIError (HTTP 502).

    `retry_after_error_seconds` pauses upstream requests after a failure
    (some providers, e.g. CelesTrak, block clients that keep retrying).
    """

    def __init__(
        self, service_name: str, ttl_seconds: float, retry_after_error_seconds: float = 0
    ) -> None:
        self.service_name = service_name
        self.ttl_seconds = ttl_seconds
        self.retry_after_error_seconds = retry_after_error_seconds
        self._value: dict[str, Any] | None = None
        self._fetched_at = 0.0
        self._failed_at: float | None = None
        self._lock = asyncio.Lock()

    async def get(self, fetch: Callable[[], Awaitable[dict[str, Any]]]) -> dict[str, Any]:
        async with self._lock:  # one refresh at a time; others wait for its result
            now = time.monotonic()
            if self._value is not None and now - self._fetched_at < self.ttl_seconds:
                return self._value
            cooling_down = (
                self._failed_at is not None and now - self._failed_at < self.retry_after_error_seconds
            )
            try:
                if cooling_down:
                    raise ValueError("upstream recently failed; not retrying yet")
                value = await fetch()
            except UPSTREAM_ERRORS as e:
                if not cooling_down:
                    self._failed_at = now
                if self._value is not None:
                    logger.warning("%s unavailable, serving cached data: %r", self.service_name, e)
                    return {**self._value, "stale": True}
                raise ExternalAPIError(
                    f"{self.service_name} unavailable", service_name=self.service_name
                ) from e
            self._value, self._fetched_at, self._failed_at = {**value, "stale": False}, now, None
            return self._value


def round_coords(value: Any, digits: int = 5) -> Any:
    """Round nested GeoJSON coordinates (~1 m) to shrink payloads."""
    if isinstance(value, float):
        return round(value, digits)
    if isinstance(value, list):
        return [round_coords(v, digits) for v in value]
    return value
