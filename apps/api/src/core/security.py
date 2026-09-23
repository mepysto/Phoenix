"""Shared request authentication dependencies."""

import hmac
from typing import Annotated

from fastapi import Header, HTTPException

from src.core.config import settings


def verify_api_key(x_api_key: Annotated[str | None, Header()] = None) -> None:
    """Require the operator API key (X-API-Key) for privileged endpoints."""
    if x_api_key is None or not hmac.compare_digest(
        x_api_key.encode(), settings.api_sync_key.encode()
    ):
        raise HTTPException(status_code=401, detail="Invalid API key")
