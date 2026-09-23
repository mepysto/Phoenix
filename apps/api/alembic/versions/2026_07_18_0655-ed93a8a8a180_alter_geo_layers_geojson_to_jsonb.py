"""alter_geo_layers_geojson_to_jsonb

Revision ID: ed93a8a8a180
Revises: add_merge_tracking_columns
Create Date: 2026-07-18 06:55:26.281333

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'ed93a8a8a180'
down_revision: Union[str, Sequence[str], None] = 'add_merge_tracking_columns'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema to alter geo_layers.geojson from Text to JSONB."""
    op.alter_column(
        'geo_layers',
        'geojson',
        existing_type=sa.TEXT(),
        type_=postgresql.JSONB(astext_type=sa.Text()),
        postgresql_using="geojson::jsonb",
        existing_nullable=False
    )


def downgrade() -> None:
    """Downgrade schema to alter geo_layers.geojson from JSONB to Text."""
    op.alter_column(
        'geo_layers',
        'geojson',
        existing_type=postgresql.JSONB(astext_type=sa.Text()),
        type_=sa.TEXT(),
        postgresql_using="geojson::text",
        existing_nullable=False
    )
