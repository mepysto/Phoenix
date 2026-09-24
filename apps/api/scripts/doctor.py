"""Check that a Phoenix environment is ready to run (``pnpm doctor``).

Required checks (non-zero exit on failure): toolchain, database connection,
PostGIS/TimescaleDB, migrations at head. Optional checks (warnings only):
upstream data/tile services and server-side API keys. Key *values* are never
printed, only whether they are set.

Usage:
    python -m scripts.doctor [--offline]
"""

import argparse
import asyncio
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from alembic.config import Config
from alembic.script import ScriptDirectory

OK, WARN, FAIL = "✓", "!", "✗"

# (name, url) — reachability only; licences are documented in docs/DATA_SOURCES.md
UPSTREAMS = [
    ("GDACS RSS", "https://www.gdacs.org/xml/rss.xml"),
    ("USGS earthquakes", "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/4.5_day.geojson"),
    ("NASA EONET", "https://eonet.gsfc.nasa.gov/api/v3/events?limit=1"),
    ("Copernicus EMS", "https://mapping.emergency.copernicus.eu/activations/api/activations/"),
    ("OpenFreeMap basemap", "https://tiles.openfreemap.org/styles/dark"),
    ("EOX Sentinel-2 cloudless", "https://tiles.maps.eox.at/wmts/1.0.0/WMTSCapabilities.xml"),
    ("NASA GIBS", "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/1.0.0/WMTSCapabilities.xml"),
    ("RainViewer radar", "https://api.rainviewer.com/public/weather-maps.json"),
    ("NASA FIRMS", "https://firms.modaps.eosdis.nasa.gov/data/active_fire/noaa-20-viirs-c2/csv/"),
    ("NOAA NHC tropical", "https://mapservices.weather.noaa.gov/tropical/rest/services/tropical/NHC_tropical_weather/MapServer?f=json"),
]

# Server-side keys: which optional layers they unlock
OPTIONAL_KEYS: dict[str, str] = {}


@dataclass
class Result:
    status: str
    name: str
    detail: str = ""

    def __str__(self) -> str:
        return f"  {self.status} {self.name}" + (f" — {self.detail}" if self.detail else "")


def _version(cmd: list[str]) -> str | None:
    if not shutil.which(cmd[0]):
        return None
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=10, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return (out.stdout or out.stderr).strip().splitlines()[0] if out.returncode == 0 else None


def check_toolchain() -> list[Result]:
    results = [
        Result(
            OK if sys.version_info >= (3, 11) else FAIL,
            "Python",
            f"{sys.version.split()[0]} (need >= 3.11)",
        )
    ]
    node = _version(["node", "--version"])
    major = int(node.lstrip("v").split(".")[0]) if node else 0
    results.append(Result(OK if major >= 20 else FAIL, "Node.js", f"{node or 'not found'} (need >= 20)"))
    pnpm = _version(["pnpm", "--version"])
    results.append(Result(OK if pnpm else FAIL, "pnpm", pnpm or "not found"))
    docker = _version(["docker", "--version"])
    results.append(Result(OK if docker else WARN, "Docker", docker or "not found (needed for the DB stack)"))
    return results


def _database_url() -> str:
    url = os.getenv("DATABASE_URL") or Config("alembic.ini").get_main_option("sqlalchemy.url", "")
    return url.replace("postgresql://", "postgresql+asyncpg://", 1)


async def check_database() -> list[Result]:
    url = _database_url()
    engine = create_async_engine(url, connect_args={"timeout": 5})
    try:
        async with engine.connect() as conn:
            extensions = set(
                (await conn.execute(text("SELECT extname FROM pg_extension"))).scalars()
            )
            has_version_table = (
                await conn.execute(text("SELECT to_regclass('public.alembic_version') IS NOT NULL"))
            ).scalar()
            current = (
                (await conn.execute(text("SELECT version_num FROM alembic_version"))).scalar()
                if has_version_table
                else None
            )
    except Exception as e:  # noqa: BLE001 — report any connection problem
        return [Result(FAIL, "Database", f"cannot connect ({type(e).__name__}); is it running?")]
    finally:
        await engine.dispose()

    head = ScriptDirectory.from_config(Config("alembic.ini")).get_current_head()
    host = url.split("@")[-1]  # never print credentials
    return [
        Result(OK, "Database", f"connected to {host}"),
        Result(OK if "postgis" in extensions else FAIL, "PostGIS extension"),
        Result(OK if "timescaledb" in extensions else WARN, "TimescaleDB extension"),
        Result(
            OK if current == head else FAIL,
            "Migrations",
            "at head" if current == head else f"at {current or 'none'}, head is {head} — run `python -m scripts.migrate`",
        ),
    ]


async def check_upstreams() -> list[Result]:
    async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:

        async def probe(name: str, url: str) -> Result:
            try:
                response = await client.get(url, headers={"User-Agent": "phoenix-doctor"})
            except httpx.HTTPError as e:
                return Result(WARN, name, f"unreachable ({type(e).__name__})")
            status = OK if response.status_code < 400 else WARN
            return Result(status, name, f"HTTP {response.status_code}")

        return list(await asyncio.gather(*(probe(n, u) for n, u in UPSTREAMS)))


def check_keys() -> list[Result]:
    if not OPTIONAL_KEYS:
        return [Result(OK, "No server keys required", "every current layer is keyless")]
    return [
        Result(OK if os.getenv(key) else WARN, key, f"{'set' if os.getenv(key) else 'not set'} — unlocks {what}")
        for key, what in OPTIONAL_KEYS.items()
    ]


async def run(offline: bool) -> int:
    sections: list[tuple[str, list[Result]]] = [
        ("Toolchain", check_toolchain()),
        ("Database", await check_database()),
        ("Server keys (optional)", check_keys()),
    ]
    if not offline:
        sections.append(("Upstream services (optional)", await check_upstreams()))

    failed = False
    for title, results in sections:
        print(f"\n{title}")
        for result in results:
            print(result)
            failed |= result.status == FAIL
    print("\n" + ("Not ready: fix the ✗ items above." if failed else "Ready."))
    return 1 if failed else 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--offline", action="store_true", help="skip upstream network checks")
    sys.exit(asyncio.run(run(parser.parse_args().offline)))


if __name__ == "__main__":
    main()
