"""
Usage:
    python -m scripts.seed_data          # Insert seed data
    python -m scripts.seed_data --clear  # Clear existing data first
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

sys.path.insert(0, str(__file__).rsplit("/scripts", 1)[0])

from src.core.config import settings
from src.models.event import Dataset, Event, EventType, GeoLayer, SeverityLevel

SEED_SOURCE_PREFIX = "seed-"


def get_database_url() -> str:
    return settings.database_url.replace("postgresql://", "postgresql+asyncpg://")


def generate_polygon_geojson(lat: float, lon: float, radius_km: float = 50) -> str:
    lat_offset = radius_km / 111.0
    lon_offset = radius_km / (111.0 * abs(float(f"{lat:.1f}") or 1))

    return json.dumps({
        "type": "Feature",
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [lon - lon_offset, lat - lat_offset],
                [lon + lon_offset, lat - lat_offset],
                [lon + lon_offset, lat + lat_offset],
                [lon - lon_offset, lat + lat_offset],
                [lon - lon_offset, lat - lat_offset],
            ]],
        },
        "properties": {},
    })


def generate_point_geojson(lat: float, lon: float) -> str:
    return json.dumps({
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [lon, lat]},
        "properties": {},
    })


def get_seed_events() -> list[dict]:
    now = datetime.now(timezone.utc)

    return [
        {
            "type": EventType.earthquake,
            "title": "M6.8 Earthquake in Ishikawa Prefecture, Japan",
            "description": "A magnitude 6.8 earthquake struck the Noto Peninsula in Ishikawa Prefecture, causing significant damage to infrastructure and buildings. Multiple aftershocks reported.",
            "severity": SeverityLevel.high,
            "latitude": 37.5,
            "longitude": 137.2,
            "country_code": "JP",
            "region": "Ishikawa Prefecture",
            "affected_population": 280000,
            "start_date": now - timedelta(days=5),
            "is_active": True,
            "source_id": f"{SEED_SOURCE_PREFIX}earthquake-japan-001",
            "source_url": "https://earthquake.usgs.gov/",
            "layers": [
                {"layer_type": "epicenter", "properties": {"magnitude": 6.8, "depth_km": 10}},
                {"layer_type": "affected_area", "radius_km": 80, "properties": {"intensity": "VII", "damage_level": "severe"}},
            ],
            "datasets": [
                {"name": "Seismic Activity Data - Ishikawa 2024", "type": "seismic", "url": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/significant_week.geojson", "license": "Public Domain"},
            ],
        },
        {
            "type": EventType.flood,
            "title": "Severe Monsoon Flooding in Sylhet, Bangladesh",
            "description": "Heavy monsoon rains have caused widespread flooding in northeastern Bangladesh, affecting millions of people. Rivers have exceeded danger levels.",
            "severity": SeverityLevel.critical,
            "latitude": 24.8949,
            "longitude": 91.8687,
            "country_code": "BD",
            "region": "Sylhet Division",
            "affected_population": 4500000,
            "start_date": now - timedelta(days=12),
            "is_active": True,
            "source_id": f"{SEED_SOURCE_PREFIX}flood-bangladesh-001",
            "source_url": "https://www.gdacs.org/",
            "layers": [
                {"layer_type": "flood_extent", "radius_km": 120, "properties": {"water_level_m": 2.5, "flood_type": "riverine"}},
            ],
            "datasets": [
                {"name": "Flood Monitoring Data - Sylhet Region", "type": "satellite_imagery", "url": "https://emergency.copernicus.eu/mapping/list-of-components", "license": "CC-BY-4.0"},
            ],
        },
        {
            "type": EventType.wildfire,
            "title": "Bushfire Emergency in New South Wales, Australia",
            "description": "Multiple bushfires burning across New South Wales with extreme fire danger conditions. Several communities under evacuation orders.",
            "severity": SeverityLevel.high,
            "latitude": -33.4839,
            "longitude": 150.1479,
            "country_code": "AU",
            "region": "New South Wales",
            "affected_population": 125000,
            "start_date": now - timedelta(days=8),
            "is_active": True,
            "source_id": f"{SEED_SOURCE_PREFIX}wildfire-australia-001",
            "source_url": "https://www.rfs.nsw.gov.au/",
            "layers": [
                {"layer_type": "fire_perimeter", "radius_km": 45, "properties": {"fire_status": "out_of_control", "hectares_burned": 85000}},
                {"layer_type": "evacuation_zone", "radius_km": 60, "properties": {"evacuation_status": "mandatory"}},
            ],
            "datasets": [],
        },
        {
            "type": EventType.hurricane,
            "title": "Hurricane Maria Category 4 - Caribbean",
            "description": "Category 4 hurricane with sustained winds of 250 km/h approaching the Lesser Antilles. Storm surge warnings in effect.",
            "severity": SeverityLevel.critical,
            "latitude": 15.3,
            "longitude": -61.4,
            "country_code": "DM",
            "region": "Dominica",
            "affected_population": 72000,
            "start_date": now - timedelta(days=3),
            "is_active": True,
            "source_id": f"{SEED_SOURCE_PREFIX}hurricane-caribbean-001",
            "source_url": "https://www.nhc.noaa.gov/",
            "layers": [
                {"layer_type": "storm_track", "properties": {"category": 4, "wind_speed_kmh": 250, "pressure_mb": 935}},
                {"layer_type": "wind_field", "radius_km": 200, "properties": {"hurricane_force_radius_km": 65}},
            ],
            "datasets": [
                {"name": "Hurricane Track Forecast Data", "type": "meteorological", "url": "https://www.nhc.noaa.gov/gis/", "license": "Public Domain"},
            ],
        },
        {
            "type": EventType.tsunami,
            "title": "Tsunami Warning - Sulawesi, Indonesia",
            "description": "Tsunami warning issued following a 7.2 magnitude undersea earthquake off the coast of Sulawesi. Coastal areas being evacuated.",
            "severity": SeverityLevel.critical,
            "latitude": -0.9,
            "longitude": 119.8,
            "country_code": "ID",
            "region": "Central Sulawesi",
            "affected_population": 350000,
            "start_date": now - timedelta(days=1),
            "is_active": True,
            "source_id": f"{SEED_SOURCE_PREFIX}tsunami-indonesia-001",
            "source_url": "https://www.tsunami.gov/",
            "layers": [
                {"layer_type": "tsunami_zone", "radius_km": 150, "properties": {"wave_height_m": 3.5, "arrival_time_min": 25}},
            ],
            "datasets": [],
        },
        {
            "type": EventType.volcano,
            "title": "Taal Volcano Eruption - Philippines",
            "description": "Phreatomagmatic eruption at Taal Volcano with ash plumes reaching 1.5km. Alert Level 3 declared, danger zone expanded.",
            "severity": SeverityLevel.high,
            "latitude": 14.0023,
            "longitude": 120.9933,
            "country_code": "PH",
            "region": "Batangas",
            "affected_population": 450000,
            "start_date": now - timedelta(days=15),
            "is_active": True,
            "source_id": f"{SEED_SOURCE_PREFIX}volcano-philippines-001",
            "source_url": "https://www.phivolcs.dost.gov.ph/",
            "layers": [
                {"layer_type": "crater", "properties": {"alert_level": 3, "ash_plume_km": 1.5}},
                {"layer_type": "danger_zone", "radius_km": 14, "properties": {"exclusion_radius_km": 14}},
            ],
            "datasets": [
                {"name": "Volcanic Activity Monitoring Data", "type": "volcanological", "url": "https://volcano.si.edu/", "license": "CC-BY-4.0"},
            ],
        },
        {
            "type": EventType.war,
            "title": "Ongoing Conflict - Kharkiv Oblast, Ukraine",
            "description": "Continued military conflict in Kharkiv region with infrastructure damage and civilian displacement. Humanitarian corridor established.",
            "severity": SeverityLevel.critical,
            "latitude": 49.9935,
            "longitude": 36.2304,
            "country_code": "UA",
            "region": "Kharkiv Oblast",
            "affected_population": 2800000,
            "start_date": now - timedelta(days=25),
            "is_active": True,
            "source_id": f"{SEED_SOURCE_PREFIX}war-ukraine-001",
            "source_url": "https://reliefweb.int/",
            "layers": [
                {"layer_type": "conflict_zone", "radius_km": 100, "properties": {"conflict_intensity": "high"}},
            ],
            "datasets": [
                {"name": "Humanitarian Situation Report - Ukraine", "type": "humanitarian", "url": "https://data.humdata.org/group/ukr", "license": "CC-BY-4.0"},
            ],
        },
        {
            "type": EventType.pollution,
            "title": "Severe Air Pollution Alert - Delhi NCR, India",
            "description": "Air quality index exceeds hazardous levels in Delhi National Capital Region. PM2.5 levels at 15x WHO safe limits. Schools closed.",
            "severity": SeverityLevel.high,
            "latitude": 28.6139,
            "longitude": 77.209,
            "country_code": "IN",
            "region": "Delhi NCR",
            "affected_population": 32000000,
            "start_date": now - timedelta(days=7),
            "is_active": True,
            "source_id": f"{SEED_SOURCE_PREFIX}pollution-india-001",
            "source_url": "https://aqicn.org/city/delhi/",
            "layers": [
                {"layer_type": "pollution_zone", "radius_km": 70, "properties": {"aqi": 485, "pm25": 380, "category": "hazardous"}},
            ],
            "datasets": [],
        },
        {
            "type": EventType.drought,
            "title": "Severe Drought - Northern Kenya",
            "description": "Prolonged drought conditions in northern Kenya affecting pastoral communities. Fourth consecutive failed rainy season. Food security crisis declared.",
            "severity": SeverityLevel.high,
            "latitude": 2.0,
            "longitude": 37.9062,
            "country_code": "KE",
            "region": "Turkana County",
            "affected_population": 4200000,
            "start_date": now - timedelta(days=20),
            "is_active": True,
            "source_id": f"{SEED_SOURCE_PREFIX}drought-kenya-001",
            "source_url": "https://fews.net/",
            "layers": [
                {"layer_type": "drought_zone", "radius_km": 200, "properties": {"drought_severity": "exceptional", "ipc_phase": 4}},
            ],
            "datasets": [
                {"name": "Food Security Analysis - East Africa", "type": "food_security", "url": "https://fews.net/east-africa/kenya", "license": "Public Domain"},
            ],
        },
        {
            "type": EventType.other,
            "title": "Chemical Plant Explosion - Tianjin Port, China",
            "description": "Large explosion at chemical storage facility in Tianjin port area. Hazardous materials released. Emergency response ongoing.",
            "severity": SeverityLevel.critical,
            "latitude": 39.0346,
            "longitude": 117.7272,
            "country_code": "CN",
            "region": "Tianjin",
            "affected_population": 175000,
            "start_date": now - timedelta(days=2),
            "is_active": True,
            "source_id": f"{SEED_SOURCE_PREFIX}other-china-001",
            "source_url": "https://reliefweb.int/",
            "layers": [
                {"layer_type": "blast_zone", "radius_km": 5, "properties": {"explosion_type": "chemical", "evacuation_radius_km": 10}},
                {"layer_type": "contamination_zone", "radius_km": 15, "properties": {"hazmat_type": "sodium_cyanide"}},
            ],
            "datasets": [],
        },
        {
            "type": EventType.earthquake,
            "title": "M5.9 Earthquake in Izmir Province, Turkey",
            "description": "Moderate earthquake struck western Turkey near Izmir. Building damage reported in urban areas. Search and rescue operations underway.",
            "severity": SeverityLevel.medium,
            "latitude": 38.4192,
            "longitude": 27.1287,
            "country_code": "TR",
            "region": "Izmir Province",
            "affected_population": 150000,
            "start_date": now - timedelta(days=10),
            "end_date": now - timedelta(days=9),
            "is_active": False,
            "source_id": f"{SEED_SOURCE_PREFIX}earthquake-turkey-001",
            "source_url": "https://earthquake.usgs.gov/",
            "layers": [
                {"layer_type": "epicenter", "properties": {"magnitude": 5.9, "depth_km": 15}},
            ],
            "datasets": [],
        },
        {
            "type": EventType.flood,
            "title": "Flash Flooding in Bavaria, Germany",
            "description": "Heavy rainfall caused flash flooding in southern Bavaria. Rivers overflowing, transportation disrupted. Emergency shelters opened.",
            "severity": SeverityLevel.medium,
            "latitude": 48.1351,
            "longitude": 11.582,
            "country_code": "DE",
            "region": "Bavaria",
            "affected_population": 85000,
            "start_date": now - timedelta(days=6),
            "end_date": now - timedelta(days=4),
            "is_active": False,
            "source_id": f"{SEED_SOURCE_PREFIX}flood-germany-001",
            "source_url": "https://www.gdacs.org/",
            "layers": [
                {"layer_type": "flood_extent", "radius_km": 40, "properties": {"water_level_m": 1.2, "flood_type": "flash"}},
            ],
            "datasets": [],
        },
    ]


async def get_existing_source_ids(session: AsyncSession, source_ids: list[str]) -> set[str]:
    result = await session.execute(select(Event.source_id).where(Event.source_id.in_(source_ids)))
    return {row[0] for row in result.fetchall() if row[0]}


async def clear_seed_data(session: AsyncSession) -> int:
    result = await session.execute(
        select(Event.id).where(Event.source_id.like(f"{SEED_SOURCE_PREFIX}%"))
    )
    event_ids = [row[0] for row in result.fetchall()]

    if not event_ids:
        return 0

    await session.execute(delete(Dataset).where(Dataset.event_id.in_(event_ids)))
    await session.execute(delete(GeoLayer).where(GeoLayer.event_id.in_(event_ids)))
    await session.execute(delete(Event).where(Event.id.in_(event_ids)))
    await session.commit()

    return len(event_ids)


async def insert_seed_data(session: AsyncSession, skip_existing: bool = True) -> dict:
    events_data = get_seed_events()
    source_ids = [e["source_id"] for e in events_data]

    existing_ids = await get_existing_source_ids(session, source_ids) if skip_existing else set()

    stats = {"events_inserted": 0, "events_skipped": 0, "layers_inserted": 0, "datasets_inserted": 0}

    for event_data in events_data:
        if event_data["source_id"] in existing_ids:
            stats["events_skipped"] += 1
            continue

        layers_data = event_data.pop("layers", [])
        datasets_data = event_data.pop("datasets", [])

        event_id = uuid4()
        event = Event(id=event_id, **event_data)
        event.affected_area_geojson = generate_polygon_geojson(event_data["latitude"], event_data["longitude"], radius_km=50)
        session.add(event)

        for layer_data in layers_data:
            layer_type = layer_data["layer_type"]
            properties = layer_data.get("properties", {})
            radius_km = layer_data.get("radius_km", 30)

            is_point_layer = layer_type in ["epicenter", "crater"]
            geojson = (
                generate_point_geojson(event_data["latitude"], event_data["longitude"])
                if is_point_layer
                else generate_polygon_geojson(event_data["latitude"], event_data["longitude"], radius_km)
            )

            layer = GeoLayer(
                id=uuid4(),
                event_id=event_id,
                layer_type=layer_type,
                geojson=geojson,
                properties=properties,
                timestamp=event_data["start_date"],
            )
            session.add(layer)
            stats["layers_inserted"] += 1

        for dataset_data in datasets_data:
            dataset = Dataset(
                id=uuid4(),
                event_id=event_id,
                name=dataset_data["name"],
                type=dataset_data.get("type"),
                url=dataset_data.get("url"),
                license=dataset_data.get("license"),
                metadata_=dataset_data.get("metadata"),
            )
            session.add(dataset)
            stats["datasets_inserted"] += 1

        stats["events_inserted"] += 1

    await session.commit()
    return stats


async def main(clear: bool = False) -> None:
    database_url = get_database_url()
    engine = create_async_engine(database_url, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    print("=" * 60)
    print("Phoenix Seed Data Script")
    print("=" * 60)
    print(f"Database: {database_url.split('@')[1] if '@' in database_url else 'local'}")
    print()

    async with async_session() as session:
        if clear:
            print("[CLEAR] Removing existing seed data...")
            deleted_count = await clear_seed_data(session)
            print(f"[CLEAR] Deleted {deleted_count} existing seed events")
            print()

        print("[INSERT] Inserting seed data...")
        stats = await insert_seed_data(session, skip_existing=not clear)

        print()
        print("=" * 60)
        print("Summary")
        print("=" * 60)
        print(f"  Events inserted:  {stats['events_inserted']}")
        print(f"  Events skipped:   {stats['events_skipped']}")
        print(f"  Layers inserted:  {stats['layers_inserted']}")
        print(f"  Datasets inserted: {stats['datasets_inserted']}")
        print()

        if stats["events_inserted"] > 0:
            print("[SUCCESS] Seed data inserted successfully!")
        elif stats["events_skipped"] > 0:
            print("[INFO] All seed data already exists. Use --clear to replace.")
        else:
            print("[WARNING] No data was inserted.")

    await engine.dispose()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Phoenix seed data script")
    parser.add_argument("--clear", action="store_true", help="Clear existing seed data before inserting")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(main(clear=args.clear))
