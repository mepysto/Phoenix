"""Load GeoNames place names for search.

Source: GeoNames cities5000 (towns over 5,000 people and administrative
seats, ~70,000 places) with region and country names. Licence: CC BY 4.0,
attribution "GeoNames" (https://www.geonames.org); see docs/DATA_SOURCES.md.

Usage:
    python -m scripts.import_places            # download and load
    python -m scripts.import_places --if-empty # skip when places are loaded
    python -m scripts.import_places --dir PATH # use local copies of the files

The load replaces the whole table in one transaction, so search keeps
working on the old data until the new data is committed.
"""

import argparse
import asyncio
import logging
import os
import re
import zipfile
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("import_places")

BASE_URL = "https://download.geonames.org/export/dump"
FILES = ("cities5000.zip", "admin1CodesASCII.txt", "countryInfo.txt")
# Safety limit only: the busiest place (all cities5000) has 263 names, ~570k in total
MAX_NAMES_PER_PLACE = 300
MAX_NAME_LENGTH = 200
# Airport/IATA-style codes ("SEL", "VLC") and links are not names people type
CODE = re.compile(r"^[A-Z0-9]{2,4}$")

Place = dict[str, Any]


def parse_admin1(lines: Iterable[str]) -> dict[str, str]:
    """'KR.11' -> 'Seoul' (admin1CodesASCII.txt: code, name, ascii name, id)"""
    out: dict[str, str] = {}
    for line in lines:
        parts = line.split("\t")
        if len(parts) >= 2 and parts[0] and not line.startswith("#"):
            out[parts[0]] = parts[1]
    return out


def parse_countries(lines: Iterable[str]) -> dict[str, str]:
    """'KR' -> 'South Korea' (countryInfo.txt; '#' lines are comments)"""
    out: dict[str, str] = {}
    for line in lines:
        if line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) >= 5 and len(parts[0]) == 2:
            out[parts[0]] = parts[4]
    return out


def search_names(name: str, ascii_name: str, alternates: Iterable[str]) -> set[str]:
    """Every name a place may be typed as, case-folded, without codes or links"""
    names: set[str] = set()
    for raw in (name, ascii_name, *alternates):
        value = raw.strip()
        if not value or CODE.match(value) or "://" in value or len(value) > MAX_NAME_LENGTH:
            continue
        names.add(value.casefold())
        if len(names) >= MAX_NAMES_PER_PLACE:
            break
    return names


def parse_cities(
    lines: Iterable[str], admin1: dict[str, str], countries: dict[str, str]
) -> Iterator[tuple[Place, set[str]]]:
    """Rows of the GeoNames 'geoname' table (tab separated, 19 columns)"""
    for line in lines:
        cols = line.split("\t")
        if len(cols) < 15 or not cols[0].isdigit():
            continue
        try:
            lat, lng = float(cols[4]), float(cols[5])
            population = int(cols[14] or 0)
        except ValueError:
            continue
        cc = cols[8]
        region = admin1.get(f"{cc}.{cols[10]}")
        place = {
            "id": int(cols[0]),
            "name": cols[1][:MAX_NAME_LENGTH],
            # "Valencia, Valencia, Spain" says nothing the place name has not said
            "admin1": region if region and region != cols[1] else None,
            "country": countries.get(cc),
            "country_code": cc[:2],
            "latitude": lat,
            "longitude": lng,
            "population": population,
        }
        yield place, search_names(cols[1], cols[2], cols[3].split(","))


def read_files(directory: Path) -> tuple[list[str], list[str], list[str]]:
    zipped = directory / "cities5000.zip"
    if zipped.exists():
        with zipfile.ZipFile(zipped) as archive:
            cities = archive.read("cities5000.txt").decode("utf-8").splitlines()
    else:
        cities = (directory / "cities5000.txt").read_text(encoding="utf-8").splitlines()
    admin1 = (directory / "admin1CodesASCII.txt").read_text(encoding="utf-8").splitlines()
    countries = (directory / "countryInfo.txt").read_text(encoding="utf-8").splitlines()
    return cities, admin1, countries


def download(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    with httpx.Client(timeout=120, follow_redirects=True) as client:
        for name in FILES:
            logger.info("Downloading %s", name)
            response = client.get(f"{BASE_URL}/{name}")
            response.raise_for_status()
            (directory / name).write_bytes(response.content)


def _database_url() -> str:
    from src.core.config import configured_database_url

    url = os.getenv("DATABASE_URL") or configured_database_url() or ""
    return url.replace("postgresql://", "postgresql+asyncpg://", 1)


async def load(places: list[tuple[Place, set[str]]], url: str, if_empty: bool = False) -> int:
    engine = create_async_engine(url)
    try:
        async with engine.begin() as conn:
            if if_empty and await conn.scalar(text("SELECT EXISTS (SELECT 1 FROM places)")):
                logger.info("Places already loaded; skipping")
                return 0
            await conn.execute(text("TRUNCATE places CASCADE"))
            raw = (await conn.get_raw_connection()).driver_connection
            columns = ["id", "name", "admin1", "country", "country_code", "latitude", "longitude", "population"]
            await raw.copy_records_to_table(
                "places", records=[tuple(p[c] for c in columns) for p, _ in places], columns=columns
            )
            await raw.copy_records_to_table(
                "place_names",
                records=[(p["id"], name) for p, names in places for name in names],
                columns=["place_id", "name"],
            )
        return len(places)
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dir", type=Path, help="folder with cities5000.zip, admin1CodesASCII.txt, countryInfo.txt")
    parser.add_argument("--if-empty", action="store_true", help="do nothing when places are already loaded")
    args = parser.parse_args()

    directory = args.dir or Path(os.getenv("TMPDIR", "/tmp")) / "phoenix-geonames"
    if not args.dir:
        download(directory)
    cities, admin1, countries = read_files(directory)
    places = list(parse_cities(cities, parse_admin1(admin1), parse_countries(countries)))
    count = asyncio.run(load(places, _database_url(), if_empty=args.if_empty))
    if count:
        logger.info("Loaded %d places (GeoNames, CC BY 4.0)", count)


if __name__ == "__main__":
    main()
