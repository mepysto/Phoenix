"""Import critical infrastructure reference data into infrastructure_assets.

Sources (both CC BY 4.0, see docs/DATA_SOURCES.md):
- WRI Global Power Plant Database v1.3 (~35k plants; frozen since 2021)
- Global Dam Watch v1 (~41k dams), EU JRC open-data mirror

Re-running updates rows in place (upsert on source + source_id).

Usage:
    python -m scripts.import_infrastructure [--only dams|power_plants]
"""

import argparse
import asyncio
import csv
import io
import logging
import math
import os
import tempfile
from collections.abc import Iterable, Iterator
from typing import Any

import httpx
from sqlalchemy import func, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.models.infrastructure import InfrastructureAsset

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("import_infrastructure")

GPPD_URL = (
    "https://raw.githubusercontent.com/wri/global-power-plant-database/master/"
    "output_database/global_power_plant_database.csv"
)
GDW_BASE = "https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/GDW/GDW_v1_delta_shp/"
GDW_FILES = [f"GDW_barriers_v1_delta.{ext}" for ext in ("shp", "shx", "dbf", "prj")]
BATCH_SIZE = 2000


def _clean(value: Any) -> Any:
    """Datasets use NaN, '' and -99 for 'unknown'."""
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, int | float) and value == -99:
        return None
    if isinstance(value, str):
        value = value.strip()
        return value or None
    return value


def _number(value: Any) -> float | None:
    value = _clean(value)
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _valid_point(lng: float | None, lat: float | None) -> bool:
    return (
        lng is not None
        and lat is not None
        and -180 <= lng <= 180
        and -90 <= lat <= 90
        and not (lng == 0 and lat == 0)  # common "missing location" placeholder
    )


def parse_power_plants(rows: Iterable[dict[str, str]]) -> Iterator[dict[str, Any]]:
    for row in rows:
        lng, lat = _number(row.get("longitude")), _number(row.get("latitude"))
        source_id = _clean(row.get("gppd_idnr"))
        if not source_id or not _valid_point(lng, lat):
            continue
        capacity = _number(row.get("capacity_mw"))
        year = _number(row.get("commissioning_year"))
        yield {
            "kind": "power_plant",
            "name": _clean(row.get("name")),
            "country": _clean(row.get("country_long")),
            "importance": capacity,
            "attributes": {
                "capacity_mw": capacity,
                "primary_fuel": _clean(row.get("primary_fuel")),
                "commissioning_year": int(year) if year else None,
                "owner": _clean(row.get("owner")),
            },
            "lng": lng,
            "lat": lat,
            "source": "wri_gppd",
            "source_id": source_id,
        }


def parse_dams(records: Iterable[dict[str, Any]]) -> Iterator[dict[str, Any]]:
    for record in records:
        lng, lat = _number(record.get("lng")), _number(record.get("lat"))
        gdw_id = _clean(record.get("GDW_ID"))
        if gdw_id is None or not _valid_point(lng, lat):
            continue
        height = _number(record.get("DAM_HGT_M"))
        year = _number(record.get("YEAR_DAM"))
        yield {
            "kind": "dam",
            "name": _clean(record.get("DAM_NAME")) or _clean(record.get("RES_NAME")),
            "country": _clean(record.get("COUNTRY")),
            "importance": height,
            "attributes": {
                "height_m": height,
                "reservoir": _clean(record.get("RES_NAME")),
                "river": _clean(record.get("RIVER")),
                "year": int(year) if year else None,
                "capacity_mcm": _number(record.get("CAP_MCM")),
                "main_use": _clean(record.get("MAIN_USE")),
                "power_mw": _number(record.get("POWER_MW")),
            },
            "lng": lng,
            "lat": lat,
            "source": "gdw_v1",
            "source_id": str(int(gdw_id)),
        }


async def upsert(session: Any, assets: Iterable[dict[str, Any]]) -> int:
    """Insert or update assets in batches; returns rows written."""
    table = InfrastructureAsset.__table__
    written = 0
    batch: list[dict[str, Any]] = []

    async def flush() -> None:
        nonlocal written
        if not batch:
            return
        rows = [
            {
                **{k: v for k, v in a.items() if k not in ("lng", "lat")},
                "location": func.ST_SetSRID(func.ST_MakePoint(a["lng"], a["lat"]), 4326),
            }
            for a in batch
        ]
        stmt = insert(table).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=["source", "source_id"],
            set_={
                c: stmt.excluded[c]
                for c in ("kind", "name", "country", "importance", "attributes", "location")
            }
            | {"imported_at": text("now()")},
        )
        await session.execute(stmt)
        written += len(batch)
        batch.clear()

    for asset in assets:
        batch.append(asset)
        if len(batch) >= BATCH_SIZE:
            await flush()
    await flush()
    return written


async def _download(client: httpx.AsyncClient, url: str) -> bytes:
    response = await client.get(url)
    response.raise_for_status()
    return response.content


async def load_power_plants(client: httpx.AsyncClient) -> list[dict[str, Any]]:
    content = await _download(client, GPPD_URL)
    return list(parse_power_plants(csv.DictReader(io.StringIO(content.decode("utf-8")))))


async def load_dams(client: httpx.AsyncClient) -> list[dict[str, Any]]:
    import geopandas as gpd  # heavy; only needed for the dam import

    with tempfile.TemporaryDirectory() as tmp:
        for name in GDW_FILES:
            with open(os.path.join(tmp, name), "wb") as f:
                f.write(await _download(client, GDW_BASE + name))
        frame = gpd.read_file(os.path.join(tmp, GDW_FILES[0]))
    records = (
        {**row, "lng": geom.x if geom is not None else None, "lat": geom.y if geom is not None else None}
        for row, geom in zip(
            frame.drop(columns="geometry").to_dict("records"), frame.geometry, strict=True
        )
    )
    return list(parse_dams(records))


async def run(only: str | None) -> None:
    url = os.getenv("DATABASE_URL", "").replace("postgresql://", "postgresql+asyncpg://", 1)
    if not url:
        raise SystemExit("DATABASE_URL is not set")
    engine = create_async_engine(url)
    async with httpx.AsyncClient(timeout=httpx.Timeout(300.0), follow_redirects=True) as client:
        loaders = {"power_plants": load_power_plants, "dams": load_dams}
        for kind, loader in loaders.items():
            if only and only != kind:
                continue
            logger.info("Downloading %s ...", kind)
            assets = await loader(client)
            async with async_sessionmaker(engine)() as session:
                written = await upsert(session, assets)
                await session.commit()
            logger.info("%s: %d assets upserted", kind, written)
    await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--only", choices=["dams", "power_plants"])
    asyncio.run(run(parser.parse_args().only))


if __name__ == "__main__":
    main()
