"""add_postgis_admin_areas

Revision ID: add_postgis_admin_areas
Revises: 7915058385b8
Create Date: 2025-12-31 01:00:00.000000

This migration:
1. Enables PostGIS extension
2. Adds new event types to event_type enum
3. Creates geo_precision and geo_method enums
4. Creates admin_areas table with spatial columns
5. Adds new columns to events table (location, geo_precision, geo_method, admin_area_id, glide_number)
6. Creates spatial indexes
7. Backfills location from existing lat/lon data
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from geoalchemy2 import Geometry
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "add_postgis_admin_areas"
down_revision: Union[str, Sequence[str], None] = "7915058385b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Apply migration: add PostGIS support, admin_areas, and new event columns."""

    # =========================================================================
    # 1. Enable PostGIS extension
    # =========================================================================
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    # =========================================================================
    # 2. Add new values to event_type enum
    # =========================================================================
    # PostgreSQL requires adding enum values one at a time
    op.execute("ALTER TYPE eventtype ADD VALUE IF NOT EXISTS 'landslide'")
    op.execute("ALTER TYPE eventtype ADD VALUE IF NOT EXISTS 'industrial'")
    op.execute("ALTER TYPE eventtype ADD VALUE IF NOT EXISTS 'epidemic'")
    op.execute("ALTER TYPE eventtype ADD VALUE IF NOT EXISTS 'storm'")
    op.execute("ALTER TYPE eventtype ADD VALUE IF NOT EXISTS 'coldwave'")
    op.execute("ALTER TYPE eventtype ADD VALUE IF NOT EXISTS 'heatwave'")
    op.execute("ALTER TYPE eventtype ADD VALUE IF NOT EXISTS 'complex_emergency'")

    # =========================================================================
    # 3. Create new enum types
    # =========================================================================
    op.execute("""
        CREATE TYPE geo_precision AS ENUM (
            'exact', 'approximate', 'admin1', 'country', 'unknown'
        )
    """)

    op.execute("""
        CREATE TYPE geo_method AS ENUM (
            'source_provided', 'geocoded', 'admin_centroid', 'manual'
        )
    """)

    # =========================================================================
    # 4. Create admin_areas table
    # =========================================================================
    op.create_table(
        "admin_areas",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("iso_a2", sa.String(length=2), nullable=True),
        sa.Column("iso_a3", sa.String(length=3), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("name_local", sa.String(length=255), nullable=True),
        sa.Column("admin_level", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("parent_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("geometry", Geometry(geometry_type="MULTIPOLYGON", srid=4326,
                                       spatial_index=False), nullable=True),
        sa.Column("centroid", Geometry(geometry_type="POINT", srid=4326,
                                       spatial_index=False), nullable=True),
        sa.Column("bbox", postgresql.JSONB(), nullable=True),
        sa.Column("population", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["parent_id"], ["admin_areas.id"]),
    )

    # Create indexes for admin_areas
    op.create_index(
        "idx_admin_areas_iso_a2",
        "admin_areas",
        ["iso_a2"],
        unique=True,
        postgresql_where=sa.text("admin_level = 0 AND iso_a2 IS NOT NULL"),
    )
    op.create_index(
        "idx_admin_areas_iso_a3",
        "admin_areas",
        ["iso_a3"],
        unique=True,
        postgresql_where=sa.text("admin_level = 0 AND iso_a3 IS NOT NULL"),
    )
    op.create_index(
        "idx_admin_areas_geometry",
        "admin_areas",
        ["geometry"],
        postgresql_using="gist",
    )
    op.create_index("idx_admin_areas_parent", "admin_areas", ["parent_id"])
    op.create_index("idx_admin_areas_level", "admin_areas", ["admin_level"])

    # =========================================================================
    # 5. Add new columns to events table
    # =========================================================================

    # Make latitude/longitude nullable (they were NOT NULL before)
    op.alter_column("events", "latitude", existing_type=sa.Float(), nullable=True)
    op.alter_column("events", "longitude", existing_type=sa.Float(), nullable=True)

    # Add PostGIS location column
    op.add_column(
        "events",
        sa.Column("location", Geometry(geometry_type="POINT", srid=4326,
                                       spatial_index=False), nullable=True),
    )

    # Add geo_precision column
    op.add_column(
        "events",
        sa.Column(
            "geo_precision",
            postgresql.ENUM("exact", "approximate", "admin1", "country", "unknown",
                           name="geo_precision", create_type=False),
            nullable=True,
            server_default="unknown",
        ),
    )

    # Add geo_method column
    op.add_column(
        "events",
        sa.Column(
            "geo_method",
            postgresql.ENUM("source_provided", "geocoded", "admin_centroid", "manual",
                           name="geo_method", create_type=False),
            nullable=True,
        ),
    )

    # Add admin_area_id column with foreign key
    op.add_column(
        "events",
        sa.Column("admin_area_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_events_admin_area",
        "events",
        "admin_areas",
        ["admin_area_id"],
        ["id"],
    )

    # Add glide_number column
    op.add_column(
        "events",
        sa.Column("glide_number", sa.String(length=50), nullable=True),
    )

    # =========================================================================
    # 6. Create indexes for new columns
    # =========================================================================
    op.create_index(
        "idx_events_location",
        "events",
        ["location"],
        postgresql_using="gist",
    )
    op.create_index("idx_events_geo_precision", "events", ["geo_precision"])
    op.create_index("idx_events_admin_area", "events", ["admin_area_id"])
    op.create_index("idx_events_glide", "events", ["glide_number"])

    # =========================================================================
    # 7. Backfill location from existing lat/lon data
    # =========================================================================
    op.execute("""
        UPDATE events
        SET location = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)
        WHERE latitude IS NOT NULL
          AND longitude IS NOT NULL
          AND location IS NULL
    """)


def downgrade() -> None:
    """Revert migration: remove PostGIS support, admin_areas, and new event columns."""

    # Drop new indexes from events
    op.drop_index("idx_events_glide", table_name="events")
    op.drop_index("idx_events_admin_area", table_name="events")
    op.drop_index("idx_events_geo_precision", table_name="events")
    op.drop_index("idx_events_location", table_name="events", postgresql_using="gist")

    # Drop foreign key and columns from events
    op.drop_constraint("fk_events_admin_area", "events", type_="foreignkey")
    op.drop_column("events", "glide_number")
    op.drop_column("events", "admin_area_id")
    op.drop_column("events", "geo_method")
    op.drop_column("events", "geo_precision")
    op.drop_column("events", "location")

    # Restore latitude/longitude to NOT NULL
    op.alter_column("events", "latitude", existing_type=sa.Float(), nullable=False)
    op.alter_column("events", "longitude", existing_type=sa.Float(), nullable=False)

    # Drop admin_areas indexes
    op.drop_index("idx_admin_areas_level", table_name="admin_areas")
    op.drop_index("idx_admin_areas_parent", table_name="admin_areas")
    op.drop_index("idx_admin_areas_geometry", table_name="admin_areas", postgresql_using="gist")
    op.drop_index("idx_admin_areas_iso_a3", table_name="admin_areas")
    op.drop_index("idx_admin_areas_iso_a2", table_name="admin_areas")

    # Drop admin_areas table
    op.drop_table("admin_areas")

    # Drop enum types
    op.execute("DROP TYPE IF EXISTS geo_method")
    op.execute("DROP TYPE IF EXISTS geo_precision")

    # Note: Cannot remove enum values in PostgreSQL, they will remain
    # The added event_type values (landslide, industrial, etc.) cannot be removed

    # Note: PostGIS extension is not dropped as other tables might depend on it
