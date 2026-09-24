"""Submarine cable simplification and endpoint (gzip-compressed)."""

import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.services import submarine_cables as cables_module
from src.services.submarine_cables import simplify

CABLES = {"features": [
    {"type": "Feature", "properties": {"id": "petal", "name": "Petal", "color": "#939597", "feature_id": "petal-0"},
     "geometry": {"type": "MultiLineString", "coordinates": [[[-38.720872617, 42.156679395], [-30.1234567, 40.9876543]]]}},
    {"type": "Feature", "properties": {"id": "bad"}, "geometry": {"type": "Point", "coordinates": [0, 0]}},
]}
LANDINGS = {"features": [
    {"type": "Feature", "properties": {"id": "leverburgh", "name": "Leverburgh, United Kingdom", "is_tbd": False},
     "geometry": {"type": "Point", "coordinates": [-7.008368065, 57.769404984]}},
    {"type": "Feature", "properties": {"id": "tbd", "name": "TBD", "is_tbd": True},
     "geometry": {"type": "Point", "coordinates": [1, 1]}},
]}


def test_simplify_keeps_lines_and_confirmed_landings_with_rounded_coordinates():
    features = simplify(CABLES, LANDINGS)["features"]
    assert [(f["properties"]["kind"], f["properties"]["id"]) for f in features] == [("cable", "petal"), ("landing", "leverburgh")]
    assert features[0]["geometry"]["coordinates"] == [[[-38.721, 42.157], [-30.123, 40.988]]]
    assert features[0]["properties"]["color"] == "#939597"
    assert features[1]["geometry"]["coordinates"] == [-7.008, 57.769]


def test_empty_upstream_is_an_error():
    with pytest.raises(ValueError):
        simplify({"features": []}, {"features": []})


def test_endpoint_is_gzipped(monkeypatch):
    big = simplify({"features": CABLES["features"] * 200}, LANDINGS)

    async def fake_get():
        return {**big, "stale": False}

    monkeypatch.setattr(cables_module.submarine_cable_service, "get", fake_get)
    response = TestClient(app).get("/api/v1/infrastructure/submarine-cables", headers={"Accept-Encoding": "gzip"})
    assert response.status_code == 200
    assert response.headers["content-encoding"] == "gzip"
    assert len(response.json()["features"]) == 201
