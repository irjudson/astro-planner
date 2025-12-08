"""Add settings tables

Revision ID: a8b2c3d4e5f6
Revises: 4e15e74c0778
Create Date: 2025-12-07 18:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a8b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '4e15e74c0778'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create app_settings table
    op.create_table('app_settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('key', sa.String(), nullable=False),
        sa.Column('value', sa.String(), nullable=False),
        sa.Column('value_type', sa.String(), nullable=False, server_default='string'),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('category', sa.String(), nullable=True),
        sa.Column('is_secret', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('key')
    )
    op.create_index(op.f('ix_app_settings_id'), 'app_settings', ['id'], unique=False)
    op.create_index(op.f('ix_app_settings_key'), 'app_settings', ['key'], unique=True)
    op.create_index(op.f('ix_app_settings_category'), 'app_settings', ['category'], unique=False)

    # Create seestar_devices table
    op.create_table('seestar_devices',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('control_host', sa.String(), nullable=True),
        sa.Column('control_port', sa.Integer(), nullable=True, server_default='4700'),
        sa.Column('is_control_enabled', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('mount_path', sa.String(), nullable=True),
        sa.Column('is_mount_enabled', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('is_default', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_index(op.f('ix_seestar_devices_id'), 'seestar_devices', ['id'], unique=False)

    # Create observing_locations table
    op.create_table('observing_locations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('elevation', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('timezone', sa.String(), nullable=True, server_default="'UTC'"),
        sa.Column('bortle_class', sa.Integer(), nullable=True),
        sa.Column('is_default', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_index(op.f('ix_observing_locations_id'), 'observing_locations', ['id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_observing_locations_id'), table_name='observing_locations')
    op.drop_table('observing_locations')

    op.drop_index(op.f('ix_seestar_devices_id'), table_name='seestar_devices')
    op.drop_table('seestar_devices')

    op.drop_index(op.f('ix_app_settings_category'), table_name='app_settings')
    op.drop_index(op.f('ix_app_settings_key'), table_name='app_settings')
    op.drop_index(op.f('ix_app_settings_id'), table_name='app_settings')
    op.drop_table('app_settings')
