"""Radio Browser station normalisation and the nearby endpoint."""

from fastapi.testclient import TestClient

from src.main import app
from src.services import radio as radio_module
from src.services.radio import station

RAW = {
    "stationuuid": "fdffc27f-a096-4be8-b3bf-2c51a943a1d1",
    "name": "Gotanno FM 89.2 ",
    "url_resolved": "https://radio.gotanno.love/;",
    "homepage": "https://stcat.com/",
    "codec": "MP3",
    "bitrate": 128,
    "countrycode": "JP",
    "language": "japanese",
    "geo_lat": 35.7652,
    "geo_long": 139.8094,
    "lastcheckok": 1,
    "lastchecktime_iso8601": "2026-09-20T20:41:00Z",
}


def test_station_is_normalised():
    s = station(RAW, 35.68, 139.76)
    assert s["name"] == "Gotanno FM 89.2"
    assert s["stream_url"] == s["listen_url"] == "https://radio.gotanno.love/;"
    assert s["on_air"] is True and s["country_code"] == "JP" and s["bitrate"] == 128
    assert 9 < s["distance_km"] < 12


def test_http_streams_are_not_playable_in_page_and_offline_is_flagged():
    s = station({**RAW, "url_resolved": "http://quincy.example.com/stream.mp3", "lastcheckok": 0}, 35.68, 139.76)
    assert s["stream_url"] is None
    assert s["listen_url"] == "http://quincy.example.com/stream.mp3"
    assert s["on_air"] is False


def test_unusable_entries():
    assert station({**RAW, "geo_lat": None}, 0, 0) is None
    s = station({**RAW, "url_resolved": "javascript:alert(1)", "homepage": "ftp://x", "bitrate": 0}, 0, 0)
    assert (s["stream_url"], s["listen_url"], s["homepage"], s["bitrate"]) == (None, None, None, None)


def test_endpoint(monkeypatch):
    async def fake_nearby(lat, lng, radius_km, limit):
        return [station(RAW, lat, lng)]

    monkeypatch.setattr(radio_module.radio_service, "nearby", fake_nearby)
    client = TestClient(app)
    body = client.get("/api/v1/radio/nearby", params={"lat": 35.68, "lng": 139.76}).json()
    assert body["stations"][0]["id"] == RAW["stationuuid"]
    assert client.get("/api/v1/radio/nearby", params={"lat": 0, "lng": 0, "radius_km": 301}).status_code == 422
