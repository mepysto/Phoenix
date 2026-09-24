"""Caltrans camera parsing and the camera endpoints (snapshot proxy)."""

import pytest
from fastapi.testclient import TestClient

from src.api.v1 import cameras as cameras_api
from src.main import app
from src.services.cameras import caltrans as caltrans_module
from src.services.cameras.caltrans import Camera, parse_district
from src.utils.safe_fetch import Fetched, UnsafeFetch


def cctv(index, lat, lng, in_service="true", url=None, name="TV102 -- I-580 : West of SR-24"):
    return {"cctv": {
        "index": str(index),
        "inService": in_service,
        "location": {"locationName": name, "latitude": str(lat), "longitude": str(lng),
                     "direction": "West", "route": "I-580"},
        "imageData": {"static": {"currentImageUpdateFrequency": "5",
                                 "currentImageURL": url or f"https://cwwp2.dot.ca.gov/data/d4/cctv/image/{index}.jpg"}},
    }}


def test_parse_district_keeps_valid_in_service_cameras():
    payload = {"data": [
        cctv(1, 37.82539, -122.27291),
        cctv(2, 37.8, -122.2, in_service="false"),
        cctv(3, "", -122.2),
        cctv(4, 37.8, -122.2, url="https://elsewhere.example.com/x.jpg"),  # off the snapshot allowlist
    ]}
    cameras = parse_district(payload, 4)
    assert [c.id for c in cameras] == ["caltrans-d4-1"]
    assert cameras[0] == Camera(
        id="caltrans-d4-1", name="TV102 -- I-580 : West of SR-24", latitude=37.82539, longitude=-122.27291,
        direction="West", route="I-580", snapshot_url="https://cwwp2.dot.ca.gov/data/d4/cctv/image/1.jpg",
        snapshot_minutes=5,
    )


@pytest.fixture
def client(monkeypatch):
    cams = parse_district({"data": [cctv(1, 37.8254, -122.2729), cctv(2, 34.05, -118.25), cctv(3, 37.83, -122.28)]}, 4)

    async def all_():
        return cams

    async def get(camera_id):
        return next((c for c in cams if c.id == camera_id), None)

    monkeypatch.setattr(caltrans_module.caltrans_cameras, "all", all_)
    monkeypatch.setattr(caltrans_module.caltrans_cameras, "get", get)
    monkeypatch.setattr(cameras_api, "_snapshots", cameras_api.OrderedDict())
    return TestClient(app)


def test_cameras_in_view(client):
    bay = client.get("/api/v1/cameras", params={"min_lng": -123, "min_lat": 37, "max_lng": -122, "max_lat": 38}).json()
    assert sorted(f["properties"]["id"] for f in bay["features"]) == ["caltrans-d4-1", "caltrans-d4-3"]


def test_nearby_cameras(client):
    near = client.get("/api/v1/cameras/nearby", params={"lat": 37.8254, "lng": -122.2729, "radius_km": 10}).json()
    assert [c["id"] for c in near] == ["caltrans-d4-1", "caltrans-d4-3"]
    assert near[0]["distance_km"] == 0.0


def test_snapshot_is_proxied_and_cached(client, monkeypatch):
    calls = []

    async def fake_get(url, hosts, **kwargs):
        calls.append((url, hosts))
        return Fetched(content=b"\xff\xd8jpeg", content_type="image/jpeg")

    monkeypatch.setattr(cameras_api, "safe_get", fake_get)
    for _ in range(2):
        response = client.get("/api/v1/cameras/caltrans-d4-1/snapshot")
        assert response.status_code == 200
        assert response.content == b"\xff\xd8jpeg"
        assert response.headers["content-type"] == "image/jpeg"
        assert response.headers["x-content-type-options"] == "nosniff"
    # The URL comes from the camera list, with the source's allowlist; second call hits the cache
    assert calls == [("https://cwwp2.dot.ca.gov/data/d4/cctv/image/1.jpg", frozenset({"cwwp2.dot.ca.gov"}))]


def test_snapshot_errors(client, monkeypatch):
    async def failing(url, hosts, **kwargs):
        raise UnsafeFetch("upstream returned 500")

    monkeypatch.setattr(cameras_api, "safe_get", failing)
    assert client.get("/api/v1/cameras/caltrans-d4-1/snapshot").status_code == 502
    assert client.get("/api/v1/cameras/caltrans-d4-99/snapshot").status_code == 404
    assert client.get("/api/v1/cameras/..%2F..%2Fetc/snapshot").status_code in (404, 422)
