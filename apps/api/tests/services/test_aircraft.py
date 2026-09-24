"""ADS-B aircraft: privacy filtering, mapping, cell sharing and the endpoint."""

from fastapi.testclient import TestClient

from src.main import app
from src.services.tracks import aircraft as aircraft_module
from src.services.tracks.aircraft import AircraftService, to_geojson

PAYLOAD = {
    "ac": [
        {"hex": "85c17d", "flight": "JAL375  ", "t": "B738", "lat": 35.5, "lon": 139.2,
         "alt_baro": 22400, "gs": 380.4, "track": 272.7, "seen": 0.0, "dbFlags": None},
        {"hex": "ae1234", "flight": "RCH123", "t": "C17", "lat": 36.0, "lon": 139.0,
         "alt_baro": 31000, "gs": 450, "track": 90, "dbFlags": 1},
        {"hex": "a00001", "flight": "N1", "lat": 35.0, "lon": 139.0, "alt_baro": 5000, "dbFlags": 8},  # LADD
        {"hex": "a00002", "lat": 35.0, "lon": 139.0, "dbFlags": 4},  # PIA
        {"hex": "a00003", "flight": "NOPOS", "alt_baro": 1000},  # no position
        {"hex": "a00004", "flight": "TAXI", "lat": 35.55, "lon": 139.78, "alt_baro": "ground"},
    ]
}


def test_privacy_programme_and_positionless_aircraft_are_dropped():
    hexes = [f["properties"]["hex"] for f in to_geojson(PAYLOAD)["features"]]
    assert hexes == ["85c17d", "ae1234", "a00004"]


def test_properties_are_mapped():
    features = {f["properties"]["hex"]: f for f in to_geojson(PAYLOAD)["features"]}
    jal = features["85c17d"]
    assert jal["geometry"]["coordinates"] == [139.2, 35.5]
    assert jal["properties"] == {
        "hex": "85c17d", "callsign": "JAL375", "type": "B738", "altitude_ft": 22400.0,
        "on_ground": False, "speed_kt": 380.4, "track_deg": 272.7, "military": False, "seen_s": 0.0,
    }
    assert features["ae1234"]["properties"]["military"] is True
    taxi = features["a00004"]["properties"]
    assert taxi["on_ground"] is True and taxi["altitude_ft"] is None


def test_nearby_viewers_share_a_cell():
    assert AircraftService.cell(35.55, 139.78, 60) == AircraftService.cell(35.6, 139.9, 70) == (35.5, 140.0, 75)
    assert AircraftService.cell(0, 0, 1)[2] == 25
    assert AircraftService.cell(0, 0, 400)[2] == 250


def test_endpoint(monkeypatch):
    seen = {}

    async def fake_around(lat, lng, radius_nm):
        seen.update(lat=lat, lng=lng, radius_nm=radius_nm)
        return {**to_geojson(PAYLOAD), "stale": False}

    monkeypatch.setattr(aircraft_module.aircraft_service, "around", fake_around)
    client = TestClient(app)
    body = client.get("/api/v1/tracks/aircraft", params={"lat": 35.5, "lng": 139.7, "radius_nm": 120}).json()
    assert len(body["features"]) == 3
    assert seen == {"lat": 35.5, "lng": 139.7, "radius_nm": 120}
    assert client.get("/api/v1/tracks/aircraft", params={"lat": 0, "lng": 0, "radius_nm": 251}).status_code == 422
