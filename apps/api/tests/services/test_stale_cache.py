"""StaleOnErrorCache: TTL, stale fallback and the post-error cool-down."""

import httpx
import pytest

from src.core.exceptions import ExternalAPIError
from src.services.hazards import cache as cache_module
from src.services.hazards.cache import StaleOnErrorCache


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


@pytest.fixture
def clock(monkeypatch):
    c = Clock()
    monkeypatch.setattr(cache_module.time, "monotonic", c)
    return c


@pytest.mark.asyncio
async def test_serves_stale_then_pauses_after_error(clock):
    calls = []

    async def failing():
        calls.append("fail")
        raise httpx.ConnectError("down")

    async def ok():
        calls.append("ok")
        return {"v": 1}

    cache = StaleOnErrorCache("Feed", ttl_seconds=60, retry_after_error_seconds=600)
    assert await cache.get(ok) == {"v": 1, "stale": False}

    clock.now += 61  # expired: refresh fails, stale data served
    assert await cache.get(failing) == {"v": 1, "stale": True}
    clock.now += 60  # within the cool-down: upstream is not called again
    assert await cache.get(failing) == {"v": 1, "stale": True}
    assert calls == ["ok", "fail"]

    clock.now += 600  # cool-down over: try again
    assert await cache.get(ok) == {"v": 1, "stale": False}
    assert calls == ["ok", "fail", "ok"]


@pytest.mark.asyncio
async def test_no_cooldown_by_default_and_502_without_data(clock):
    calls = []

    async def failing():
        calls.append(1)
        raise httpx.ConnectError("down")

    cache = StaleOnErrorCache("Feed", ttl_seconds=60)
    for _ in range(2):
        with pytest.raises(ExternalAPIError):
            await cache.get(failing)
    assert len(calls) == 2
