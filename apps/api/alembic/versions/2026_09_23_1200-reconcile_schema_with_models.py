"""Reconcile the migrated schema with the SQLAlchemy models.

Databases built only from Alembic drifted from the models (and from the
legacy infrastructure/docker/init-db.sql). This migration is idempotent so it
can run on both kinds of databases:

- rename enums eventtype/severitylevel -> event_type/severity_level
- add the 7 data_sources operational columns
- widen events.country_code to 3 chars (ISO alpha-3)
- add the unique (source_id, external_id) index required by the
  event_sources upsert (ON CONFLICT)
- add the admin_areas centroid GiST index
- convert event_metrics to a TimescaleDB hypertable when the extension exists

Revision ID: reconcile_schema_with_models
Revises: ed93a8a8a180
Create Date: 2026-09-23 12:00:00
"""

from collections.abc import Sequence

from alembic import op

revision: str = "reconcile_schema_with_models"
down_revision: str | None = "ed93a8a8a180"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


NOT_NULL_WITH_BACKFILL: tuple[tuple[str, str, str], ...] = (
    ("admin_areas", "created_at", "now()"),
    ("admin_areas", "updated_at", "now()"),
    ("data_sources", "api_key_required", "false"),
    ("data_sources", "is_active", "true"),
    ("data_sources", "consecutive_failures", "0"),
    ("data_sources", "is_realtime", "false"),
    ("datasets", "created_at", "now()"),
    ("event_sources", "fetched_at", "now()"),
    ("events", "is_active", "true"),
    ("events", "created_at", "now()"),
    ("events", "updated_at", "now()"),
    ("geo_layers", "created_at", "now()"),
)
NOT_NULL_FOREIGN_KEYS: tuple[tuple[str, str], ...] = (
    ("datasets", "event_id"),
    ("event_sources", "event_id"),
    ("event_sources", "source_id"),
    ("geo_layers", "event_id"),
)


def _rename_enum(old: str, new: str) -> None:
    op.execute(
        f"""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_type WHERE typname = '{old}')
               AND NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = '{new}') THEN
                ALTER TYPE {old} RENAME TO {new};
            END IF;
        END $$;
        """
    )


def upgrade() -> None:
    _rename_enum("eventtype", "event_type")
    _rename_enum("severitylevel", "severity_level")

    op.execute(
        """
        ALTER TABLE data_sources
            ADD COLUMN IF NOT EXISTS auth_type VARCHAR(20),
            ADD COLUMN IF NOT EXISTS sync_interval_minutes INTEGER DEFAULT 5,
            ADD COLUMN IF NOT EXISTS rate_limit_rpm INTEGER,
            ADD COLUMN IF NOT EXISTS last_sync_status VARCHAR(20) DEFAULT 'never',
            ADD COLUMN IF NOT EXISTS last_sync_error TEXT,
            ADD COLUMN IF NOT EXISTS consecutive_failures INTEGER NOT NULL DEFAULT 0,
            ADD COLUMN IF NOT EXISTS is_realtime BOOLEAN NOT NULL DEFAULT false
        """
    )

    op.execute("ALTER TABLE events ALTER COLUMN country_code TYPE VARCHAR(3)")

    # Fails loudly if duplicate (source_id, external_id) rows exist: those are
    # data errors that must be resolved deliberately, not silently deleted.
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_event_sources_source_external
            ON event_sources (source_id, external_id)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_admin_areas_centroid
            ON admin_areas USING gist (centroid)
        """
    )

    # Legacy init-db.sql declared these nullable; the models require values.
    for table, column, fill in NOT_NULL_WITH_BACKFILL:
        op.execute(f"UPDATE {table} SET {column} = {fill} WHERE {column} IS NULL")
        op.execute(f"ALTER TABLE {table} ALTER COLUMN {column} SET NOT NULL")
    # No safe backfill for foreign keys: fail loudly if orphaned rows exist.
    for table, column in NOT_NULL_FOREIGN_KEYS:
        op.execute(f"ALTER TABLE {table} ALTER COLUMN {column} SET NOT NULL")

    # Legacy indexes were declared DESC; recreate them as the models define them.
    op.execute("DROP INDEX IF EXISTS idx_events_start_date")
    op.execute("CREATE INDEX idx_events_start_date ON events (start_date)")
    op.execute("DROP INDEX IF EXISTS idx_event_metrics_event_id")
    op.execute("CREATE INDEX idx_event_metrics_event_id ON event_metrics (event_id, time)")

    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'timescaledb') THEN
                PERFORM create_hypertable(
                    'event_metrics', 'time',
                    if_not_exists => TRUE, migrate_data => TRUE
                );
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    # Hypertable conversion and enum renames are intentionally not reverted.
    op.execute("DROP INDEX IF EXISTS idx_admin_areas_centroid")
    op.execute("DROP INDEX IF EXISTS idx_event_sources_source_external")
    op.execute(
        """
        ALTER TABLE data_sources
            DROP COLUMN IF EXISTS auth_type,
            DROP COLUMN IF EXISTS sync_interval_minutes,
            DROP COLUMN IF EXISTS rate_limit_rpm,
            DROP COLUMN IF EXISTS last_sync_status,
            DROP COLUMN IF EXISTS last_sync_error,
            DROP COLUMN IF EXISTS consecutive_failures,
            DROP COLUMN IF EXISTS is_realtime
        """
    )
