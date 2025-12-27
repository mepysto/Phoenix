"""baseline_initial_schema

Revision ID: 7915058385b8
Revises:
Create Date: 2025-12-26 20:40:04.015360

This is a baseline migration that represents the initial schema.
It matches the current SQLAlchemy models and the existing database schema.

For existing databases: Run `alembic stamp head` to mark this as applied.
For new databases: This migration creates all tables from scratch.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "7915058385b8"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Define enum types
eventtype_enum = postgresql.ENUM(
    "earthquake",
    "flood",
    "wildfire",
    "hurricane",
    "tsunami",
    "volcano",
    "war",
    "pollution",
    "drought",
    "other",
    name="eventtype",
    create_type=False,
)

severitylevel_enum = postgresql.ENUM(
    "low",
    "medium",
    "high",
    "critical",
    name="severitylevel",
    create_type=False,
)


def upgrade() -> None:
    """Create all tables for Phoenix schema."""
    # Create enum types
    op.execute("CREATE TYPE eventtype AS ENUM "
               "('earthquake', 'flood', 'wildfire', 'hurricane', 'tsunami', "
               "'volcano', 'war', 'pollution', 'drought', 'other')")
    op.execute("CREATE TYPE severitylevel AS ENUM ('low', 'medium', 'high', 'critical')")

    # Create events table
    op.create_table(
        "events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, default=sa.text("gen_random_uuid()")),
        sa.Column("type", eventtype_enum, nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("severity", severitylevel_enum, nullable=False, server_default="medium"),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("affected_area_geojson", sa.Text(), nullable=True),
        sa.Column("country_code", sa.String(length=2), nullable=True),
        sa.Column("region", sa.String(length=255), nullable=True),
        sa.Column("affected_population", sa.Integer(), nullable=True),
        sa.Column("start_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("source_id", sa.String(length=255), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_events_lat_lon", "events", ["latitude", "longitude"])
    op.create_index("idx_events_type", "events", ["type"])
    op.create_index("idx_events_severity", "events", ["severity"])
    op.create_index("idx_events_start_date", "events", ["start_date"])
    op.create_index("idx_events_is_active", "events", ["is_active"])
    op.create_index("idx_events_source_id", "events", ["source_id"])

    # Create data_sources table
    op.create_table(
        "data_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(length=255), nullable=False, unique=True),
        sa.Column("type", sa.String(length=50), nullable=False),
        sa.Column("api_url", sa.Text(), nullable=True),
        sa.Column("api_key_required", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("update_frequency", sa.String(length=50), nullable=True),
        sa.Column("last_sync", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    # Create event_sources table (junction table)
    op.create_table(
        "event_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, default=sa.text("gen_random_uuid()")),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=True),
        sa.Column("raw_data", postgresql.JSONB(), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_id"], ["data_sources.id"]),
    )

    # Create geo_layers table
    op.create_table(
        "geo_layers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, default=sa.text("gen_random_uuid()")),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("layer_type", sa.String(length=100), nullable=False),
        sa.Column("geojson", sa.Text(), nullable=False),
        sa.Column("properties", postgresql.JSONB(), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
    )
    op.create_index("idx_geo_layers_event_id", "geo_layers", ["event_id"])

    # Create datasets table
    op.create_table(
        "datasets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, default=sa.text("gen_random_uuid()")),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=500), nullable=False),
        sa.Column("type", sa.String(length=100), nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("license", sa.String(length=255), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
    )

    # Create event_metrics table (for TimescaleDB hypertable)
    op.create_table(
        "event_metrics",
        sa.Column("time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("metric_type", sa.String(length=100), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint("time", "event_id", "metric_type"),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
    )
    op.create_index("idx_event_metrics_event_id", "event_metrics", ["event_id", "time"])

    # Note: TimescaleDB hypertable creation should be done separately
    # as Alembic doesn't directly support it:
    # SELECT create_hypertable('event_metrics', 'time', if_not_exists => TRUE);


def downgrade() -> None:
    """Drop all tables and types."""
    op.drop_table("event_metrics")
    op.drop_table("datasets")
    op.drop_table("geo_layers")
    op.drop_table("event_sources")
    op.drop_table("data_sources")
    op.drop_table("events")

    op.execute("DROP TYPE IF EXISTS severitylevel")
    op.execute("DROP TYPE IF EXISTS eventtype")
