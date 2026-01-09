"""add_merge_tracking_columns

Revision ID: add_merge_tracking_columns
Revises: add_postgis_admin_areas
Create Date: 2026-01-05 00:00:00.000000

This migration adds columns for tracking offline merge operations:
- merged_into_id: UUID FK to events.id (the canonical event this was merged into)
- is_canonical: BOOLEAN (whether this event is the canonical/primary event)
- CHECK constraint: id != merged_into_id (prevent self-merge)
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "add_merge_tracking_columns"
down_revision: Union[str, Sequence[str], None] = "add_postgis_admin_areas"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add merge tracking columns to events table."""

    # Add merged_into_id column (FK to events.id)
    op.add_column(
        "events",
        sa.Column("merged_into_id", postgresql.UUID(as_uuid=True), nullable=True),
    )

    # Add is_canonical column (default TRUE for all existing events)
    op.add_column(
        "events",
        sa.Column(
            "is_canonical",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )

    # Create foreign key constraint
    op.create_foreign_key(
        "fk_events_merged_into",
        "events",
        "events",
        ["merged_into_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Create index on merged_into_id for efficient lookups
    op.create_index(
        "idx_events_merged_into",
        "events",
        ["merged_into_id"],
    )

    # Create index on is_canonical for filtering canonical events
    op.create_index(
        "idx_events_is_canonical",
        "events",
        ["is_canonical"],
    )

    # Add CHECK constraint to prevent self-merge
    op.create_check_constraint(
        "chk_events_no_self_merge",
        "events",
        "id != merged_into_id",
    )


def downgrade() -> None:
    """Remove merge tracking columns from events table."""

    # Drop CHECK constraint
    op.drop_constraint("chk_events_no_self_merge", "events", type_="check")

    # Drop indexes
    op.drop_index("idx_events_is_canonical", table_name="events")
    op.drop_index("idx_events_merged_into", table_name="events")

    # Drop foreign key
    op.drop_constraint("fk_events_merged_into", "events", type_="foreignkey")

    # Drop columns
    op.drop_column("events", "is_canonical")
    op.drop_column("events", "merged_into_id")
