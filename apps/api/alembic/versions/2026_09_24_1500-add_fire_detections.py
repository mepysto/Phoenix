"""Add fire_detections (NASA FIRMS active fires).

Revision ID: add_fire_detections
Revises: add_infrastructure_assets
Create Date: 2026-09-24 15:00:00
"""

from collections.abc import Sequence

import geoalchemy2
import sqlalchemy as sa

from alembic import op

revision: str = "add_fire_detections"
down_revision: str | None = "add_infrastructure_assets"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "fire_detections",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("satellite", sa.String(16), nullable=False),
        sa.Column("instrument", sa.String(8), nullable=False),
        sa.Column("acquired_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("frp", sa.Float()),
        sa.Column("brightness_k", sa.Float()),
        sa.Column("confidence", sa.String(16)),
        sa.Column("daynight", sa.String(1)),
        sa.Column(
            "location",
            geoalchemy2.Geometry("POINT", srid=4326, spatial_index=False),
            nullable=False,
        ),
    )
    op.create_index(
        "idx_fire_detections_identity",
        "fire_detections",
        ["satellite", "acquired_at", "latitude", "longitude"],
        unique=True,
    )
    op.create_index("idx_fire_detections_acquired_at", "fire_detections", ["acquired_at"])
    op.execute(
        "CREATE INDEX idx_fire_detections_location ON fire_detections USING gist (location)"
    )


def downgrade() -> None:
    op.drop_table("fire_detections")
