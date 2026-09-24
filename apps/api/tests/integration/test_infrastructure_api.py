"""Infrastructure viewport query against PostGIS (TEST_DATABASE_URL)."""

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from scripts.import_infrastructure import parse_dams, parse_power_plants, upsert
from src.db.database import get_db
from src.main import app

DB_URL = os.getenv("TEST_DATABASE_URL", "").replace("postgresql://", "postgresql+asyncpg://", 1)
pytestmark = pytest.mark.skipif(not DB_URL, reason="TEST_DATABASE_URL not set")


def plant(pid: str, lng: float, lat: float, mw: float) -> dict:
    return {"gppd_idnr": pid, "name": pid, "country_long": "X", "capacity_mw": str(mw),
            "latitude": str(lat), "longitude": str(lng), "primary_fuel": "Hydro"}


@pytest.fixture
async def seeded():
    engine = create_async_engine(DB_URL)
    async with async_sessionmaker(engine)() as session:
        await session.execute(text("TRUNCATE infrastructure_assets"))
        await upsert(session, parse_power_plants([
            plant("tokyo-small", 139.7, 35.7, 50),
            plant("tokyo-big", 139.8, 35.6, 900),
            plant("fiji", 178.0, -17.7, 10),
            plant("samoa", -172.0, -13.8, 20),
        ]))
        await upsert(session, parse_dams([
            {"GDW_ID": 1, "DAM_NAME": "Kurobe", "DAM_HGT_M": 186, "lng": 137.66, "lat": 36.57},
            {"GDW_ID": 2, "DAM_NAME": "Unknown height", "DAM_HGT_M": -99, "lng": 139.0, "lat": 36.0},
        ]))
        await session.commit()
    yield
    await engine.dispose()


@pytest.fixture
def client():
    """App client whose DB sessions don't pool connections across event loops
    (each TestClient runs its own loop)."""
    engine = create_async_engine(DB_URL, poolclass=NullPool)
    maker = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db():
        async with maker() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.pop(get_db, None)


def _get(client: TestClient, **params):
    return client.get("/api/v1/infrastructure", params=params)


def test_viewport_returns_most_significant_first(seeded, client) -> None:
    body = _get(client, min_lng=130, min_lat=30, max_lng=145, max_lat=40).json()
    names = [f["properties"]["name"] for f in body["features"]]
    assert names[:3] == ["tokyo-big", "Kurobe", "tokyo-small"]
    assert names[-1] == "Unknown height"  # unknown importance last
    assert body["truncated"] is False


def test_limit_sets_truncated(seeded, client) -> None:
    body = _get(client, min_lng=130, min_lat=30, max_lng=145, max_lat=40, limit=2).json()
    assert len(body["features"]) == 2 and body["truncated"] is True


def test_kind_filter_and_antimeridian(seeded, client) -> None:
    body = _get(client, min_lng=170, min_lat=-30, max_lng=-170, max_lat=0, kinds=["power_plant"]).json()
    assert sorted(f["properties"]["name"] for f in body["features"]) == ["fiji", "samoa"]
    dams = _get(client, min_lng=130, min_lat=30, max_lng=145, max_lat=40, kinds=["dam"]).json()
    assert {f["properties"]["kind"] for f in dams["features"]} == {"dam"}


@pytest.mark.asyncio
async def test_reimport_updates_in_place(seeded) -> None:
    engine = create_async_engine(DB_URL)
    async with async_sessionmaker(engine)() as session:
        await upsert(session, parse_power_plants([plant("fiji", 178.0, -17.7, 99)]))
        await session.commit()
        count, importance = (
            await session.execute(
                text("SELECT count(*), max(importance) FROM infrastructure_assets WHERE source_id='fiji'")
            )
        ).one()
    await engine.dispose()
    assert count == 1 and importance == 99
