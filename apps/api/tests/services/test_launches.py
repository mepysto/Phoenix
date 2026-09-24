"""Launch Library 2 mapping and the launches endpoint."""

from fastapi.testclient import TestClient

from src.main import app
from src.services.tracks import launches as launches_module
from src.services.tracks.launches import to_geojson

PAYLOAD = {"results": [
    {"id": "a", "name": "Long March 8A | SatNet LEO Group 26", "net": "2026-09-23T13:32:00Z",
     "status": {"abbrev": "Success"}, "launch_service_provider": {"abbrev": "CASC", "name": "China Aerospace"},
     "mission": {"type": "Communications", "orbit": {"abbrev": "LEO"}},
     "pad": {"name": "Commercial LC-1", "latitude": 19.597275, "longitude": 110.930753}},
    {"id": "b", "name": "No pad position", "pad": {"latitude": None, "longitude": None}},
    {"id": "c", "name": "Bad latitude", "pad": {"latitude": "95", "longitude": "10"}},
    {"id": "d", "name": "Minimal", "pad": {"latitude": "28.5", "longitude": "-80.6"}},
]}


def test_launches_become_pad_points():
    features = to_geojson(PAYLOAD)["features"]
    assert [f["properties"]["id"] for f in features] == ["a", "d"]
    assert features[0]["geometry"]["coordinates"] == [110.93075, 19.59727]  # round() on binary floats
    assert features[0]["properties"] == {
        "id": "a", "name": "Long March 8A | SatNet LEO Group 26", "net": "2026-09-23T13:32:00Z",
        "status": "Success", "provider": "CASC", "mission_type": "Communications", "orbit": "LEO",
        "pad": "Commercial LC-1",
    }
    assert features[1]["properties"]["provider"] is None


def test_endpoint(monkeypatch):
    async def fake_upcoming():
        return {**to_geojson(PAYLOAD), "stale": False}

    monkeypatch.setattr(launches_module.launch_service, "upcoming", fake_upcoming)
    assert len(TestClient(app).get("/api/v1/tracks/launches").json()["features"]) == 2
