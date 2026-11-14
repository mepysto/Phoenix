"""Place search against PostgreSQL (TEST_DATABASE_URL), loaded from real GeoNames sample rows."""

import asyncio
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from scripts.import_places import load, parse_admin1, parse_cities, parse_countries, read_files
from src.main import app
from tests.integration import test_plans_api as plans

pytestmark = plans.pytestmark
world = plans.world  # points the app at the test database
FIXTURES = Path(__file__).parent.parent / "fixtures" / "geonames"
SEARCH = "/api/v1/places/search"


@pytest.fixture
async def client(world):
    cities, admin1, countries = read_files(FIXTURES)
    places = list(parse_cities(cities, parse_admin1(admin1), parse_countries(countries)))
    assert await load(places, plans.DB_URL) == 5
    return TestClient(app)


def _names(client: TestClient, q: str) -> list[str]:
    r = client.get(SEARCH, params={"q": q})
    assert r.status_code == 200, r.text
    return [f'{p["name"]}, {p["country"]}' for p in r.json()["data"]]


def test_prefix_search_in_any_language_and_case(client):
    assert "Seoul, South Korea" in _names(client, "seo")
    assert _names(client, "서울") == ["Seoul, South Korea"]
    assert _names(client, "SÉOUL") == ["Seoul, South Korea"]
    assert _names(client, "maput") == ["Maputo, Mozambique"]


def test_main_names_outrank_alternates(client):
    # Shenzhen is larger and one of its alternate names starts with "seo"
    assert _names(client, "seo")[0] == "Seoul, South Korea"


def test_larger_places_come_first_and_context_is_given(client):
    body = client.get(SEARCH, params={"q": "valencia"}).json()["data"]
    assert [(p["country_code"], p["admin1"]) for p in body] == [("VE", "Carabobo"), ("ES", None)]
    assert {"lat", "lng", "population", "id"} <= body[0].keys()


def test_wildcards_are_literal_and_input_is_bounded(client):
    assert _names(client, "%a") == []
    assert _names(client, "s_oul") == []
    assert client.get(SEARCH, params={"q": "s"}).status_code == 422
    assert client.get(SEARCH, params={"q": "x" * 101}).status_code == 422
    assert client.get(SEARCH, params={"q": "valencia", "limit": 1}).json()["data"][0]["country_code"] == "VE"


def test_reload_replaces_rather_than_duplicates(client):
    cities, admin1, countries = read_files(FIXTURES)
    places = list(parse_cities(cities, parse_admin1(admin1), parse_countries(countries)))
    assert asyncio.run(load(places, plans.DB_URL)) == 5
    assert asyncio.run(load(places, plans.DB_URL, if_empty=True)) == 0
    assert _names(client, "서울") == ["Seoul, South Korea"]

