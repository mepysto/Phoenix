"""Re-key GDACS event_sources to "<eventtype>-<eventid>".

GDACS eventids are only unique per hazard type (EQ 1000 and TC 1000 are
different events), so the ingestion key now includes the type code. Existing
rows are rewritten so the next sync matches them instead of creating
duplicates. raw_data.event_type_code has been stored since the first GDACS
ingestion.

Revision ID: rekey_gdacs_external_ids
Revises: reconcile_schema_with_models
Create Date: 2026-09-23 13:00:00
"""

from collections.abc import Sequence

from alembic import op

revision: str = "rekey_gdacs_external_ids"
down_revision: str | None = "reconcile_schema_with_models"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE event_sources es
        SET external_id = (es.raw_data->>'event_type_code') || '-' || es.external_id
        FROM data_sources ds
        WHERE es.source_id = ds.id
          AND ds.name = 'GDACS'
          AND COALESCE(es.raw_data->>'event_type_code', '') <> ''
          AND es.external_id NOT LIKE (es.raw_data->>'event_type_code') || '-%'
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE event_sources es
        SET external_id = substr(es.external_id, length(es.raw_data->>'event_type_code') + 2)
        FROM data_sources ds
        WHERE es.source_id = ds.id
          AND ds.name = 'GDACS'
          AND COALESCE(es.raw_data->>'event_type_code', '') <> ''
          AND es.external_id LIKE (es.raw_data->>'event_type_code') || '-%'
        """
    )
