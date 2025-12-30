#!/usr/bin/env python
"""
Natural Earth Countries Data Import Script

Downloads Natural Earth country boundary data and imports it into the PostGIS admin_areas table.

Usage:
    python -m scripts.import_natural_earth                          # Default 110m resolution
    python -m scripts.import_natural_earth --resolution 10m         # High resolution
    python -m scripts.import_natural_earth --file /path/to/file.shp # Local file
    python -m scripts.import_natural_earth --db-url postgresql://...

Data Source:
    Natural Earth - Public Domain map data
    https://www.naturalearthdata.com/
"""

from __future__ import annotations

import argparse
import logging
import sys
import tempfile
from pathlib import Path
from typing import Any
from uuid import uuid4

import geopandas as gpd
import pandas as pd
from shapely import wkb
from shapely.geometry import MultiPolygon, Polygon, mapping
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Natural Earth data URLs
NATURAL_EARTH_URLS = {
    "110m": "https://naciscdn.org/naturalearth/110m/cultural/ne_110m_admin_0_countries.zip",
    "50m": "https://naciscdn.org/naturalearth/50m/cultural/ne_50m_admin_0_countries.zip",
    "10m": "https://naciscdn.org/naturalearth/10m/cultural/ne_10m_admin_0_countries.zip",
}

# Column mapping from Natural Earth to our schema
# Natural Earth has various column names depending on version
COLUMN_MAPPING = {
    # ISO codes - try multiple possible column names
    "iso_a2": ["ISO_A2", "iso_a2", "ISO_A2_EH"],
    "iso_a3": ["ISO_A3", "iso_a3", "ISO_A3_EH", "ADM0_ISO", "ADM0_A3"],
    # Name columns
    "name": ["NAME", "name", "ADMIN", "NAME_EN"],
    "name_local": ["NAME_ZH", "NAME_LOCAL", "NAME_CIAWF"],
    # Population (optional)
    "population": ["POP_EST", "pop_est", "POP_RANK"],
}


def get_sync_database_url(db_url: str | None = None) -> str:
    """Get synchronous database URL for GeoPandas.
    
    GeoPandas uses psycopg2 which requires sync connections.
    """
    url = db_url or settings.database_url
    # Ensure we use psycopg2 (sync) driver, not asyncpg
    if "postgresql+asyncpg://" in url:
        url = url.replace("postgresql+asyncpg://", "postgresql://")
    elif not url.startswith("postgresql://"):
        # Handle other variants
        url = url.replace("postgres://", "postgresql://")
    return url


def find_column(gdf: gpd.GeoDataFrame, candidates: list[str]) -> str | None:
    """Find the first matching column from a list of candidates."""
    for col in candidates:
        if col in gdf.columns:
            return col
    return None


def clean_iso_code(value: Any, length: int) -> str | None:
    """Clean ISO code, returning None for invalid values."""
    if value is None or pd.isna(value):
        return None
    value_str = str(value).strip()
    # Natural Earth uses '-99' or '-' for missing/disputed ISO codes
    if value_str in ("-99", "-", "", "nan", "None"):
        return None
    if len(value_str) != length:
        return None
    return value_str.upper()


def ensure_multipolygon(geom) -> MultiPolygon | None:
    """Convert geometry to MultiPolygon if needed."""
    if geom is None:
        return None
    if isinstance(geom, MultiPolygon):
        return geom
    if isinstance(geom, Polygon):
        return MultiPolygon([geom])
    # For GeometryCollection or other types, try to extract polygons
    try:
        if hasattr(geom, "geoms"):
            polygons = [g for g in geom.geoms if isinstance(g, (Polygon, MultiPolygon))]
            if polygons:
                all_polys = []
                for p in polygons:
                    if isinstance(p, Polygon):
                        all_polys.append(p)
                    elif isinstance(p, MultiPolygon):
                        all_polys.extend(p.geoms)
                return MultiPolygon(all_polys) if all_polys else None
    except Exception:
        pass
    return None


def calculate_bbox(geom) -> dict | None:
    """Calculate bounding box as dict."""
    if geom is None:
        return None
    try:
        bounds = geom.bounds  # (minx, miny, maxx, maxy)
        return {
            "minx": float(bounds[0]),
            "miny": float(bounds[1]),
            "maxx": float(bounds[2]),
            "maxy": float(bounds[3]),
        }
    except Exception:
        return None


def load_natural_earth_data(
    file_path: str | None = None,
    resolution: str = "110m",
) -> gpd.GeoDataFrame:
    """Load Natural Earth data from URL or local file.
    
    Args:
        file_path: Path to local shapefile (optional)
        resolution: Resolution for download (110m, 50m, 10m)
        
    Returns:
        GeoDataFrame with country boundaries
    """
    if file_path:
        logger.info(f"Loading data from local file: {file_path}")
        gdf = gpd.read_file(file_path)
    else:
        url = NATURAL_EARTH_URLS.get(resolution)
        if not url:
            raise ValueError(f"Unknown resolution: {resolution}. Use: {list(NATURAL_EARTH_URLS.keys())}")
        
        logger.info(f"Downloading Natural Earth data ({resolution})...")
        logger.info(f"URL: {url}")
        
        # GeoPandas can read directly from URL (will download and extract)
        gdf = gpd.read_file(url)
    
    logger.info(f"Loaded {len(gdf)} features")
    logger.info(f"Available columns: {list(gdf.columns)}")
    
    return gdf


def transform_data(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Transform Natural Earth data to match admin_areas schema.
    
    Args:
        gdf: Raw GeoDataFrame from Natural Earth
        
    Returns:
        Transformed GeoDataFrame ready for import
    """
    logger.info("Transforming data to admin_areas schema...")
    
    # Find columns
    iso_a2_col = find_column(gdf, COLUMN_MAPPING["iso_a2"])
    iso_a3_col = find_column(gdf, COLUMN_MAPPING["iso_a3"])
    name_col = find_column(gdf, COLUMN_MAPPING["name"])
    name_local_col = find_column(gdf, COLUMN_MAPPING["name_local"])
    pop_col = find_column(gdf, COLUMN_MAPPING["population"])
    
    if not name_col:
        raise ValueError("Could not find name column in data")
    
    logger.info(f"Column mapping: iso_a2={iso_a2_col}, iso_a3={iso_a3_col}, name={name_col}")
    
    # Ensure CRS is WGS84 (EPSG:4326)
    if gdf.crs is None:
        logger.warning("No CRS defined, assuming EPSG:4326")
        gdf = gdf.set_crs(epsg=4326)
    elif gdf.crs.to_epsg() != 4326:
        logger.info(f"Reprojecting from {gdf.crs} to EPSG:4326")
        gdf = gdf.to_crs(epsg=4326)
    
    # Build transformed dataframe
    records = []
    skipped = 0
    
    for idx, row in gdf.iterrows():
        name = row.get(name_col) if name_col else None
        if not name or pd.isna(name):
            logger.warning(f"Skipping row {idx}: missing name")
            skipped += 1
            continue
        
        # Clean ISO codes
        iso_a2 = clean_iso_code(row.get(iso_a2_col) if iso_a2_col else None, 2)
        iso_a3 = clean_iso_code(row.get(iso_a3_col) if iso_a3_col else None, 3)
        
        # Ensure geometry is MultiPolygon
        geom = ensure_multipolygon(row.geometry)
        if geom is None:
            logger.warning(f"Skipping {name}: invalid geometry")
            skipped += 1
            continue
        
        # Calculate centroid
        centroid = geom.centroid
        
        # Calculate bbox
        bbox = calculate_bbox(geom)
        
        # Get population if available
        population = None
        if pop_col and row.get(pop_col) is not None:
            try:
                pop_val = row.get(pop_col)
                if not pd.isna(pop_val):
                    population = int(float(pop_val))
            except (ValueError, TypeError):
                pass
        
        # Name local
        name_local = None
        if name_local_col and row.get(name_local_col):
            nl = row.get(name_local_col)
            if not pd.isna(nl):
                name_local = str(nl)
        
        records.append({
            "id": uuid4(),
            "iso_a2": iso_a2,
            "iso_a3": iso_a3,
            "name": str(name),
            "name_local": name_local,
            "admin_level": 0,  # Country level
            "parent_id": None,
            "geometry": geom,
            "centroid": centroid,
            "bbox": bbox,
            "population": population,
        })
    
    logger.info(f"Transformed {len(records)} countries, skipped {skipped}")
    
    # Create new GeoDataFrame
    result = gpd.GeoDataFrame(records, geometry="geometry", crs="EPSG:4326")
    
    return result


def upsert_to_database(
    gdf: gpd.GeoDataFrame,
    db_url: str,
    dry_run: bool = False,
) -> dict[str, int]:
    """Upsert country data to admin_areas table.
    
    Uses SQL upsert (INSERT ... ON CONFLICT) for efficient updates.
    
    Args:
        gdf: Transformed GeoDataFrame
        db_url: PostgreSQL connection URL
        dry_run: If True, don't actually write to database
        
    Returns:
        Stats dict with inserted/updated/skipped counts
    """
    stats = {"inserted": 0, "updated": 0, "skipped": 0, "errors": 0}
    
    if dry_run:
        logger.info("[DRY RUN] Would insert/update %d countries", len(gdf))
        return stats
    
    engine = create_engine(db_url)
    
    try:
        with engine.connect() as conn:
            # Start transaction
            trans = conn.begin()
            
            try:
                for _, row in gdf.iterrows():
                    try:
                        # Convert geometries to WKB hex for PostGIS
                        geom_wkb = row.geometry.wkb_hex if row.geometry else None
                        centroid_wkb = row.centroid.wkb_hex if row.centroid else None
                        
                        # Check if record exists (by iso_a2 or iso_a3 for countries)
                        existing = None
                        if row.iso_a2:
                            result = conn.execute(
                                text("SELECT id FROM admin_areas WHERE iso_a2 = :iso_a2 AND admin_level = 0"),
                                {"iso_a2": row.iso_a2}
                            )
                            existing = result.fetchone()
                        elif row.iso_a3:
                            result = conn.execute(
                                text("SELECT id FROM admin_areas WHERE iso_a3 = :iso_a3 AND admin_level = 0"),
                                {"iso_a3": row.iso_a3}
                            )
                            existing = result.fetchone()
                        
                        if existing:
                            # Update existing record
                            conn.execute(
                                text("""
                                    UPDATE admin_areas SET
                                        iso_a2 = :iso_a2,
                                        iso_a3 = :iso_a3,
                                        name = :name,
                                        name_local = :name_local,
                                        geometry = ST_GeomFromWKB(:geometry::bytea, 4326),
                                        centroid = ST_GeomFromWKB(:centroid::bytea, 4326),
                                        bbox = :bbox::jsonb,
                                        population = :population,
                                        updated_at = NOW()
                                    WHERE id = :id
                                """),
                                {
                                    "id": existing[0],
                                    "iso_a2": row.iso_a2,
                                    "iso_a3": row.iso_a3,
                                    "name": row["name"],
                                    "name_local": row.name_local,
                                    "geometry": f"\\x{geom_wkb}" if geom_wkb else None,
                                    "centroid": f"\\x{centroid_wkb}" if centroid_wkb else None,
                                    "bbox": str(row.bbox).replace("'", '"') if row.bbox else None,
                                    "population": row.population,
                                }
                            )
                            stats["updated"] += 1
                            logger.debug(f"Updated: {row['name']} ({row.iso_a2})")
                        else:
                            # Insert new record
                            conn.execute(
                                text("""
                                    INSERT INTO admin_areas (
                                        id, iso_a2, iso_a3, name, name_local, admin_level,
                                        geometry, centroid, bbox, population, created_at, updated_at
                                    ) VALUES (
                                        :id, :iso_a2, :iso_a3, :name, :name_local, :admin_level,
                                        ST_GeomFromWKB(:geometry::bytea, 4326),
                                        ST_GeomFromWKB(:centroid::bytea, 4326),
                                        :bbox::jsonb, :population, NOW(), NOW()
                                    )
                                """),
                                {
                                    "id": str(row.id),
                                    "iso_a2": row.iso_a2,
                                    "iso_a3": row.iso_a3,
                                    "name": row["name"],
                                    "name_local": row.name_local,
                                    "admin_level": row.admin_level,
                                    "geometry": f"\\x{geom_wkb}" if geom_wkb else None,
                                    "centroid": f"\\x{centroid_wkb}" if centroid_wkb else None,
                                    "bbox": str(row.bbox).replace("'", '"') if row.bbox else None,
                                    "population": row.population,
                                }
                            )
                            stats["inserted"] += 1
                            logger.debug(f"Inserted: {row['name']} ({row.iso_a2})")
                            
                    except SQLAlchemyError as e:
                        logger.error(f"Error processing {row['name']}: {e}")
                        stats["errors"] += 1
                        continue
                
                # Commit transaction
                trans.commit()
                logger.info("Transaction committed successfully")
                
            except Exception as e:
                trans.rollback()
                logger.error(f"Transaction rolled back due to error: {e}")
                raise
                
    finally:
        engine.dispose()
    
    return stats


def import_natural_earth(
    file_path: str | None = None,
    resolution: str = "110m",
    db_url: str | None = None,
    dry_run: bool = False,
) -> dict[str, int]:
    """Main import function.
    
    Args:
        file_path: Path to local shapefile (optional)
        resolution: Resolution for Natural Earth download
        db_url: Database URL (uses settings if not provided)
        dry_run: If True, don't write to database
        
    Returns:
        Stats dict with counts
    """
    # Get database URL
    sync_db_url = get_sync_database_url(db_url)
    
    logger.info("=" * 60)
    logger.info("Natural Earth Import Script")
    logger.info("=" * 60)
    
    # Load data
    gdf = load_natural_earth_data(file_path=file_path, resolution=resolution)
    
    # Transform data
    gdf_transformed = transform_data(gdf)
    
    # Show sample
    logger.info("\nSample data (first 5 rows):")
    for _, row in gdf_transformed.head().iterrows():
        logger.info(f"  {row['name']} ({row['iso_a2']}/{row['iso_a3']})")
    
    # Upsert to database
    logger.info("\nImporting to database...")
    stats = upsert_to_database(gdf_transformed, sync_db_url, dry_run=dry_run)
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("Import Summary")
    logger.info("=" * 60)
    logger.info(f"  Inserted: {stats['inserted']}")
    logger.info(f"  Updated:  {stats['updated']}")
    logger.info(f"  Errors:   {stats['errors']}")
    logger.info("=" * 60)
    
    return stats


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Import Natural Earth country boundaries into admin_areas table",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Download and import 110m resolution data (recommended for most use cases)
    python -m scripts.import_natural_earth

    # Use higher resolution data (10m or 50m)
    python -m scripts.import_natural_earth --resolution 10m

    # Import from local file
    python -m scripts.import_natural_earth --file /path/to/ne_110m_admin_0_countries.shp

    # Dry run (don't write to database)
    python -m scripts.import_natural_earth --dry-run

    # Use custom database URL
    python -m scripts.import_natural_earth --db-url postgresql://user:pass@localhost/db
        """,
    )
    
    parser.add_argument(
        "--resolution",
        type=str,
        default="110m",
        choices=["110m", "50m", "10m"],
        help="Natural Earth resolution (default: 110m)",
    )
    
    parser.add_argument(
        "--file",
        type=str,
        help="Path to local shapefile instead of downloading",
    )
    
    parser.add_argument(
        "--db-url",
        type=str,
        help="Database URL (default: from settings)",
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't write to database, just show what would be done",
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose (debug) logging",
    )
    
    return parser.parse_args()


def main() -> None:
    """Main entry point."""
    args = parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        stats = import_natural_earth(
            file_path=args.file,
            resolution=args.resolution,
            db_url=args.db_url,
            dry_run=args.dry_run,
        )
        
        if stats["errors"] > 0:
            logger.warning(f"Completed with {stats['errors']} errors")
            sys.exit(1)
        else:
            logger.info("Import completed successfully!")
            sys.exit(0)
            
    except Exception as e:
        logger.exception(f"Import failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
