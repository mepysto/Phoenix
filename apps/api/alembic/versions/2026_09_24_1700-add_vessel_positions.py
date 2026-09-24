"""Add vessel_positions (AIS ships near active disasters).

Revision ID: add_vessel_positions
Revises: add_agent_usage
Create Date: 2026-09-24 17:00:00
"""

from collections.abc import Sequence

import geoalchemy2
import sqlalchemy as sa

from alembic import op

revision: str = "add_vessel_positions"
down_revision: str | None = "add_agent_usage"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "vessel_positions",
        sa.Column("mmsi", sa.BigInteger(), primary_key=True),
        sa.Column("name", sa.String(32)),
        sa.Column("ship_type", sa.Integer()),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("speed_kn", sa.Float()),
        sa.Column("course_deg", sa.Float()),
        sa.Column("heading_deg", sa.Float()),
        sa.Column(
            "location",
            geoalchemy2.Geometry("POINT", srid=4326, spatial_index=False),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_vessel_positions_updated_at", "vessel_positions", ["updated_at"])
    op.execute("CREATE INDEX idx_vessel_positions_location ON vessel_positions USING gist (location)")


def downgrade() -> None:
    op.drop_table("vessel_positions")
