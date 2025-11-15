"""add_catalog_tables

Revision ID: 79478a6f4f48
Revises: 9a50fa4a1d87
Create Date: 2025-11-15 07:18:27.171196

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '79478a6f4f48'
down_revision: Union[str, Sequence[str], None] = '9a50fa4a1d87'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - create catalog tables only."""
    # Only create catalog tables (processing tables created in 9a50fa4a1d87)
    op.create_table('comet_catalog',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('designation', sa.String(length=50), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=True),
    sa.Column('discovery_date', sa.Date(), nullable=True),
    sa.Column('epoch_jd', sa.Float(), nullable=False),
    sa.Column('perihelion_distance_au', sa.Float(), nullable=False),
    sa.Column('eccentricity', sa.Float(), nullable=False),
    sa.Column('inclination_deg', sa.Float(), nullable=False),
    sa.Column('arg_perihelion_deg', sa.Float(), nullable=False),
    sa.Column('ascending_node_deg', sa.Float(), nullable=False),
    sa.Column('perihelion_time_jd', sa.Float(), nullable=False),
    sa.Column('absolute_magnitude', sa.Float(), nullable=False),
    sa.Column('magnitude_slope', sa.Float(), nullable=False),
    sa.Column('current_magnitude', sa.Float(), nullable=True),
    sa.Column('activity_status', sa.String(length=20), nullable=True),
    sa.Column('comet_type', sa.String(length=20), nullable=True),
    sa.Column('data_source', sa.String(length=100), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('designation')
    )
    op.create_index(op.f('ix_comet_catalog_id'), 'comet_catalog', ['id'], unique=False)

    op.create_table('constellation_names',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('abbreviation', sa.String(length=3), nullable=False),
    sa.Column('full_name', sa.String(length=50), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('abbreviation')
    )
    op.create_index(op.f('ix_constellation_names_id'), 'constellation_names', ['id'], unique=False)

    op.create_table('dso_catalog',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('catalog_name', sa.String(length=10), nullable=False),
    sa.Column('catalog_number', sa.Integer(), nullable=False),
    sa.Column('common_name', sa.String(length=100), nullable=True),
    sa.Column('ra_hours', sa.Float(), nullable=False),
    sa.Column('dec_degrees', sa.Float(), nullable=False),
    sa.Column('object_type', sa.String(length=50), nullable=False),
    sa.Column('magnitude', sa.Float(), nullable=True),
    sa.Column('surface_brightness', sa.Float(), nullable=True),
    sa.Column('size_major_arcmin', sa.Float(), nullable=True),
    sa.Column('size_minor_arcmin', sa.Float(), nullable=True),
    sa.Column('constellation', sa.String(length=3), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_dso_catalog_id'), 'dso_catalog', ['id'], unique=False)


def downgrade() -> None:
    """Downgrade schema - drop catalog tables only."""
    # Only drop catalog tables that were created in THIS migration
    # Processing tables were created in 9a50fa4a1d87, not here
    op.drop_index(op.f('ix_dso_catalog_id'), table_name='dso_catalog')
    op.drop_table('dso_catalog')
    op.drop_index(op.f('ix_constellation_names_id'), table_name='constellation_names')
    op.drop_table('constellation_names')
    op.drop_index(op.f('ix_comet_catalog_id'), table_name='comet_catalog')
    op.drop_table('comet_catalog')
