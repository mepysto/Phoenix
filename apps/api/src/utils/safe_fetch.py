"""Fetching third-party media for the proxy without opening an SSRF hole.

Rules (defence in depth; callers should also never take URLs from clients):
- https only, and the host must be on the caller's allowlist (exact match)
- every address the host resolves to must be public (no loopback, private,
  link-local, multicast or reserved ranges), so an allowlisted name that
  points inside our network is refused
- no redirects (a redirect could leave the allowlist)
- response size, time and content type are capped

Remaining risk: DNS could change between our check and httpx's own lookup
(rebinding). That requires control of an allowlisted domain's DNS; the
allowlist only contains public-agency hosts.
"""

import asyncio
import ipaddress
import socket
from dataclasses import dataclass
from urllib.parse import urlsplit

import httpx


class UnsafeFetch(Exception):
    """The request was refused or the response broke a limit (maps to 4xx/502)."""


@dataclass(frozen=True)
class Fetched:
    content: bytes
    content_type: str


async def _resolve(host: str) -> list[tuple]:
    return await asyncio.get_running_loop().getaddrinfo(host, 443, type=socket.SOCK_STREAM)


async def _public_addresses(host: str) -> list[str]:
    try:
        infos = await _resolve(host)
    except socket.gaierror as e:
        raise UnsafeFetch(f"cannot resolve {host}") from e
    addresses = sorted({info[4][0] for info in infos})
    for address in addresses:
        ip = ipaddress.ip_address(address.split("%")[0])
        if not ip.is_global or ip.is_multicast:
            raise UnsafeFetch(f"{host} resolves to a non-public address")
    if not addresses:
        raise UnsafeFetch(f"cannot resolve {host}")
    return addresses


def check_url(url: str, allowed_hosts: frozenset[str]) -> str:
    """Validate scheme/host/port; returns the host."""
    parts = urlsplit(url)
    if parts.scheme != "https":
        raise UnsafeFetch("only https is allowed")
    host = (parts.hostname or "").lower()
    if host not in allowed_hosts:
        raise UnsafeFetch(f"host {host!r} is not allowed")
    if parts.port not in (None, 443):
        raise UnsafeFetch("non-standard port")
    if parts.username or parts.password:
        raise UnsafeFetch("credentials in URL")
    return host


async def safe_get(
    url: str,
    allowed_hosts: frozenset[str],
    *,
    max_bytes: int,
    timeout_seconds: float,
    content_type_prefix: str,
    client: httpx.AsyncClient | None = None,
    user_agent: str = "Phoenix-disaster-map/0.1 (+https://github.com/mepysto/Phoenix)",
) -> Fetched:
    host = check_url(url, allowed_hosts)
    await _public_addresses(host)
    own = client is None
    client = client or httpx.AsyncClient(timeout=timeout_seconds, follow_redirects=False)
    try:
        # Overall deadline: httpx timeouts are per operation, a slow trickle could run on
        async with asyncio.timeout(timeout_seconds):
            async with client.stream("GET", url, headers={"User-Agent": user_agent}) as response:
                if response.is_redirect:
                    raise UnsafeFetch("redirects are not followed")
                if response.status_code != 200:
                    raise UnsafeFetch(f"upstream returned {response.status_code}")
                content_type = response.headers.get("content-type", "").split(";")[0].strip().lower()
                if not content_type.startswith(content_type_prefix):
                    raise UnsafeFetch(f"unexpected content type {content_type!r}")
                declared = response.headers.get("content-length")
                if declared and declared.isdigit() and int(declared) > max_bytes:
                    raise UnsafeFetch("response too large")
                chunks, size = [], 0
                async for chunk in response.aiter_bytes():
                    size += len(chunk)
                    if size > max_bytes:
                        raise UnsafeFetch("response too large")
                    chunks.append(chunk)
                return Fetched(content=b"".join(chunks), content_type=content_type)
    except TimeoutError as e:
        raise UnsafeFetch("upstream timed out") from e
    except httpx.HTTPError as e:
        raise UnsafeFetch(f"upstream error: {type(e).__name__}") from e
    finally:
        if own:
            await client.aclose()
