"""places: GeoNames place names for search

Revision ID: add_places
Revises: add_challenges
Create Date: 2026-11-14 21:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'add_places'
down_revision: Union[str, Sequence[str], None] = 'add_challenges'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'places',
        sa.Column('id', sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('admin1', sa.String(length=200), nullable=True),
        sa.Column('country', sa.String(length=100), nullable=True),
        sa.Column('country_code', sa.String(length=2), nullable=False),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('population', sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'place_names',
        sa.Column('place_id', sa.BigInteger(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.ForeignKeyConstraint(['place_id'], ['places.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('place_id', 'name'),
    )
    op.create_index(
        'idx_place_names_prefix', 'place_names', ['name'], unique=False,
        postgresql_ops={'name': 'text_pattern_ops'},
    )


def downgrade() -> None:
    op.drop_index('idx_place_names_prefix', table_name='place_names')
    op.drop_table('place_names')
    op.drop_table('places')
