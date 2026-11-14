"""Browser origins the API answers: the exact CORS_ORIGINS list plus CORS_ORIGIN_REGEX.

The same check gates CORS responses and the /ws/events WebSocket, so a page
opened through a Tailscale name (http://linux-dev:23100) gets both its fetches
and its live updates.
"""

import pytest

from src.core.config import Settings

TAILNET_REGEX = r"^http://(linux-dev(\.tail749304\.ts\.net)?|100\.\d{1,3}\.\d{1,3}\.\d{1,3}):23100$"


def _settings(monkeypatch, origins: str, regex: str | None) -> Settings:
    monkeypatch.setenv("CORS_ORIGINS", origins)
    if regex is None:
        monkeypatch.delenv("CORS_ORIGIN_REGEX", raising=False)
    else:
        monkeypatch.setenv("CORS_ORIGIN_REGEX", regex)
    monkeypatch.setenv("ENVIRONMENT", "development")
    return Settings(_env_file=None)


def test_listed_origin_is_allowed_without_a_regex(monkeypatch):
    s = _settings(monkeypatch, "http://localhost:23100", None)

    assert s.is_allowed_origin("http://localhost:23100")
    assert not s.is_allowed_origin("http://linux-dev:23100")


@pytest.mark.parametrize(
    "origin",
    [
        "http://linux-dev:23100",
        "http://linux-dev.tail749304.ts.net:23100",
        "http://100.103.195.109:23100",
    ],
)
def test_regex_admits_tailnet_names_and_addresses(monkeypatch, origin):
    s = _settings(monkeypatch, "http://localhost:23100", TAILNET_REGEX)

    assert s.is_allowed_origin(origin)


@pytest.mark.parametrize(
    "origin",
    [
        "http://evil.example",
        "http://linux-dev.evil.example:23100",  # must match the whole origin
        "http://linux-dev:23100.evil.example",
        "http://100.103.195.109:9999",
    ],
)
def test_regex_rejects_other_sites(monkeypatch, origin):
    s = _settings(monkeypatch, "http://localhost:23100", TAILNET_REGEX)

    assert not s.is_allowed_origin(origin)


def test_regex_is_refused_in_production(monkeypatch):
    monkeypatch.setenv("CORS_ORIGIN_REGEX", TAILNET_REGEX)
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("API_SYNC_KEY", "x" * 32)
    monkeypatch.setenv("AUTH_DEV_RETURN_LINK", "false")

    with pytest.raises(ValueError, match="CORS_ORIGIN_REGEX"):
        Settings(_env_file=None)
