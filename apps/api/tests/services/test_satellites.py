"""Satellite positions and passes (SGP4 via skyfield) on fixed element sets."""

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.services.tracks import satellites as sat_module
from src.services.tracks.satellites import (
    SatelliteService,
    find_passes,
    parse_tle,
    positions_geojson,
    solar_elevation_deg,
)

# CelesTrak "resource" group, epoch 2026-09-23 (day 266)
TLE = """SENTINEL-1A
1 39634U 14016A   26266.95583925  .00000028  00000+0  15467-4 0  9991
2 39634  98.1598 272.9400 0001449  85.9652 274.1714 14.59807083664427
SENTINEL-2A
1 40697U 15028A   26266.95592176 -.00000062  00000+0 -70586-5 0  9998
2 40697  98.5666 340.3688 0001106  84.2082 275.9226 14.30816791587858
LANDSAT 9
1 49260U 21088A   26266.94377364  .00000206  00000+0  55877-4 0  9998
2 49260  98.2191 335.8779 0001464  93.1652 266.9714 14.57101826265380
"""
NOW = datetime(2026, 9, 24, 0, 0, tzinfo=UTC)
TOKYO = (35.68, 139.76)


@pytest.fixture
def sats():
    return SatelliteService._build(TLE, NOW)


def test_parse_tle_skips_garbage():
    text = "<html>error</html>\n" + TLE + "BROKEN\n1 only one line\n"
    assert [name for name, _, _ in parse_tle(text)] == ["SENTINEL-1A", "SENTINEL-2A", "LANDSAT 9"]


def test_stale_elements_are_dropped():
    assert len(SatelliteService._build(TLE, datetime(2026, 11, 1, tzinfo=UTC))) == 0


def test_positions_are_low_earth_orbit(sats):
    features = positions_geojson(sats, NOW)["features"]
    assert [f["properties"]["norad_id"] for f in features] == [39634, 40697, 49260]
    for f in features:
        lng, lat = f["geometry"]["coordinates"]
        assert -180 <= lng <= 180 and -90 <= lat <= 90
        assert 650 < f["properties"]["altitude_km"] < 850  # sun-synchronous imagers (height varies along the orbit)


def test_solar_elevation_known_values():
    # Tokyo near the September equinox: ~54 degrees at solar noon, far below at midnight
    assert solar_elevation_deg(*TOKYO, datetime(2026, 9, 23, 2, 25, tzinfo=UTC)) == pytest.approx(54.5, abs=1)
    assert solar_elevation_deg(*TOKYO, datetime(2026, 9, 23, 14, 25, tzinfo=UTC)) < -45


def test_passes_are_ordered_and_sun_synchronous(sats):
    passes = find_passes(sats, *TOKYO, NOW, 48, 30)
    assert passes, "three polar imagers pass over Tokyo within 48 h"
    assert passes == sorted(passes, key=lambda p: p.culmination)
    for p in passes:
        assert p.rise < p.culmination < p.set
        assert 30 <= p.max_elevation_deg <= 90
    # Sentinel-2's daytime passes happen mid-morning local time (10:30 descending node)
    s2_day = [p for p in passes if p.name == "SENTINEL-2A" and p.daylight]
    assert s2_day
    assert all(9 <= (p.culmination.hour + 9) % 24 <= 12 for p in s2_day)


def test_passes_endpoint(sats, monkeypatch):
    async def fake_satellites(now=None):
        return sats

    monkeypatch.setattr(sat_module.satellite_service, "satellites", fake_satellites)
    monkeypatch.setattr(sat_module.satellite_service, "_passes", {})
    client = TestClient(app)
    body = client.get(
        "/api/v1/tracks/satellites/passes", params={"lat": TOKYO[0], "lng": TOKYO[1], "daylight_only": True}
    ).json()
    assert all(p["daylight"] for p in body["passes"])
    assert body["min_elevation_deg"] == 30
    assert client.get("/api/v1/tracks/satellites/passes", params={"lat": 0, "lng": 0, "hours": 49}).status_code == 422
    positions = client.get("/api/v1/tracks/satellites", params={"at": "2026-09-24T00:00:00Z"}).json()
    assert len(positions["features"]) == 3
