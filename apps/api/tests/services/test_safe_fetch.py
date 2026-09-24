"""SSRF guards of the media proxy fetcher."""

import socket

import httpx
import pytest

from src.utils import safe_fetch
from src.utils.safe_fetch import UnsafeFetch, check_url, safe_get

HOSTS = frozenset({"cams.example.gov"})


def resolves_to(address):
    async def resolve(host):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (address, 443))]

    return resolve


def client(handler):
    return httpx.AsyncClient(transport=httpx.MockTransport(handler), follow_redirects=False)


def image(content=b"\xff\xd8jpeg", content_type="image/jpeg", status=200, headers=None):
    def handler(request):
        return httpx.Response(status, content=content, headers={"content-type": content_type, **(headers or {})})

    return handler


@pytest.mark.parametrize(
    "url",
    [
        "http://cams.example.gov/a.jpg",  # not https
        "https://evil.example.com/a.jpg",  # not allowlisted
        "https://cams.example.gov.evil.com/a.jpg",  # suffix trick
        "https://cams.example.gov:8443/a.jpg",  # other port
        "https://user:pw@cams.example.gov/a.jpg",  # credentials
        "file:///etc/passwd",
    ],
)
def test_url_checks(url):
    with pytest.raises(UnsafeFetch):
        check_url(url, HOSTS)


@pytest.mark.asyncio
@pytest.mark.parametrize("address", ["127.0.0.1", "10.0.0.5", "169.254.169.254", "192.168.1.1", "::1", "fd00::1"])
async def test_allowlisted_host_resolving_inside_is_refused(monkeypatch, address):
    monkeypatch.setattr(safe_fetch, "_resolve", resolves_to(address))
    with pytest.raises(UnsafeFetch, match="non-public"):
        await safe_get("https://cams.example.gov/a.jpg", HOSTS, max_bytes=100, timeout_seconds=5,
                       content_type_prefix="image/", client=client(image()))


@pytest.fixture
def public(monkeypatch):
    monkeypatch.setattr(safe_fetch, "_resolve", resolves_to("93.184.216.34"))


async def fetch(handler, max_bytes=1000):
    return await safe_get("https://cams.example.gov/a.jpg", HOSTS, max_bytes=max_bytes, timeout_seconds=5,
                          content_type_prefix="image/", client=client(handler))


@pytest.mark.asyncio
async def test_fetches_an_image(public):
    fetched = await fetch(image())
    assert fetched.content == b"\xff\xd8jpeg" and fetched.content_type == "image/jpeg"


@pytest.mark.asyncio
async def test_limits(public):
    with pytest.raises(UnsafeFetch, match="too large"):
        await fetch(image(content=b"x" * 2000))
    with pytest.raises(UnsafeFetch, match="too large"):
        await fetch(image(headers={"content-length": "999999"}))
    with pytest.raises(UnsafeFetch, match="content type"):
        await fetch(image(content_type="text/html"))
    with pytest.raises(UnsafeFetch, match="redirect"):
        await fetch(image(status=302, headers={"location": "http://169.254.169.254/"}))
    with pytest.raises(UnsafeFetch, match="404"):
        await fetch(image(status=404))
