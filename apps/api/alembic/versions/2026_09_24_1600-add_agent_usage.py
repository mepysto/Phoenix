"""Add agent_usage (map agent token caps).

Revision ID: add_agent_usage
Revises: add_fire_detections
Create Date: 2026-09-24 16:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "add_agent_usage"
down_revision: str | None = "add_fire_detections"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "agent_usage",
        sa.Column("day", sa.Date(), primary_key=True),
        sa.Column("session_id", sa.UUID(), primary_key=True),
        sa.Column("input_tokens", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("requests", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_table("agent_usage")
