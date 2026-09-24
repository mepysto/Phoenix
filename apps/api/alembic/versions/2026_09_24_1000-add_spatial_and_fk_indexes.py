"""Add geography GiST index and missing foreign-key indexes.

- idx_events_location_geog: ST_DWithin(geography(location), ...) (radius
  search, dedup candidates) could not use the geometry GiST index and
  scanned every canonical event (110 ms -> 9 ms at 50k events).
- event_sources.event_id / datasets.event_id: foreign keys used by joins,
  eager loading and merge relinking had no index.
- events.created_at: offline merge filters by it.

Revision ID: add_spatial_and_fk_indexes
Revises: rekey_gdacs_external_ids
Create Date: 2026-09-24 10:00:00
"""

from collections.abc import Sequence

from alembic import op

revision: str = "add_spatial_and_fk_indexes"
down_revision: str | None = "rekey_gdacs_external_ids"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

INDEXES = (
    ("idx_events_location_geog", "events USING gist (geography(location))"),
    ("idx_events_created_at", "events (created_at)"),
    ("idx_event_sources_event_id", "event_sources (event_id)"),
    ("idx_datasets_event_id", "datasets (event_id)"),
)


def upgrade() -> None:
    for name, target in INDEXES:
        op.execute(f"CREATE INDEX IF NOT EXISTS {name} ON {target}")


def downgrade() -> None:
    for name, _ in INDEXES:
        op.execute(f"DROP INDEX IF EXISTS {name}")
