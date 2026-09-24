"""Add infrastructure_assets (dams, power plants).

Revision ID: add_infrastructure_assets
Revises: add_spatial_and_fk_indexes
Create Date: 2026-09-24 14:00:00
"""

from collections.abc import Sequence

import geoalchemy2
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "add_infrastructure_assets"
down_revision: str | None = "add_spatial_and_fk_indexes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "infrastructure_assets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("name", sa.String(255)),
        sa.Column("country", sa.String(100)),
        sa.Column("importance", sa.Float()),
        sa.Column("attributes", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column(
            "location",
            geoalchemy2.Geometry("POINT", srid=4326, spatial_index=False),
            nullable=False,
        ),
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("source_id", sa.String(128), nullable=False),
        sa.Column(
            "imported_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "idx_infrastructure_source_ref",
        "infrastructure_assets",
        ["source", "source_id"],
        unique=True,
    )
    op.create_index(
        "idx_infrastructure_kind_importance", "infrastructure_assets", ["kind", "importance"]
    )
    op.execute(
        "CREATE INDEX idx_infrastructure_assets_location "
        "ON infrastructure_assets USING gist (location)"
    )


def downgrade() -> None:
    op.drop_table("infrastructure_assets")
