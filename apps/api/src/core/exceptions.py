"""
Custom exceptions for the Phoenix API.
"""


class PhoenixError(Exception):
    """Base exception for all Phoenix-related errors."""

    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ExternalAPIError(PhoenixError):
    """
    Exception raised when an external API call fails.

    This is used for errors from external services like GDACS, Copernicus, etc.
    """

    def __init__(
        self,
        message: str,
        service_name: str,
        status_code: int | None = None,
        details: dict | None = None,
    ) -> None:
        super().__init__(message, details)
        self.service_name = service_name
        self.status_code = status_code

    def __str__(self) -> str:
        base = f"[{self.service_name}] {self.message}"
        if self.status_code:
            base += f" (HTTP {self.status_code})"
        return base


class DataSyncError(PhoenixError):
    """
    Exception raised when data synchronization fails.

    This is used when sync operations fail after all retry attempts.
    """

    def __init__(
        self,
        message: str,
        source: str,
        retry_count: int = 0,
        details: dict | None = None,
    ) -> None:
        super().__init__(message, details)
        self.source = source
        self.retry_count = retry_count

    def __str__(self) -> str:
        return f"[{self.source}] {self.message} (after {self.retry_count} retries)"
