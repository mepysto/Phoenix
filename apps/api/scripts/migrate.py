"""Bring the database schema to Alembic head (single source of truth).

Handles databases that were created by the legacy
infrastructure/docker/init-db.sql (tables exist, no alembic_version): those
already match the schema up to `add_postgis_admin_areas`, so they are stamped
there before upgrading.

Usage:
    python -m scripts.migrate
"""

import asyncio
import logging
import os

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from alembic import command
from alembic.config import Config

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("migrate")

# Last revision whose schema the legacy init-db.sql fully contains
LEGACY_INIT_SQL_REVISION = "add_postgis_admin_areas"


async def _is_legacy_database(url: str) -> bool:
    engine = create_async_engine(url)
    try:
        async with engine.connect() as conn:
            result = await conn.execute(
                text(
                    "SELECT to_regclass('public.events') IS NOT NULL, "
                    "to_regclass('public.alembic_version') IS NOT NULL"
                )
            )
            has_events, has_version = result.one()
    finally:
        await engine.dispose()
    return bool(has_events) and not has_version


def _database_url(cfg: Config) -> str:
    """Resolve the URL the same way alembic/env.py does."""
    url = os.getenv("DATABASE_URL") or cfg.get_main_option("sqlalchemy.url", "")
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


def main() -> None:
    cfg = Config("alembic.ini")
    url = _database_url(cfg)
    if asyncio.run(_is_legacy_database(url)):
        logger.info("Legacy init-db.sql schema detected; stamping %s", LEGACY_INIT_SQL_REVISION)
        command.stamp(cfg, LEGACY_INIT_SQL_REVISION)
    command.upgrade(cfg, "head")
    logger.info("Database schema is at head")


if __name__ == "__main__":
    main()
