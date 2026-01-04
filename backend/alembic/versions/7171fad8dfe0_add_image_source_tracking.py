"""add_image_source_tracking

Revision ID: 7171fad8dfe0
Revises: e0daecb94db3
Create Date: 2026-01-04 23:09:31.380198

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7171fad8dfe0'
down_revision: Union[str, Sequence[str], None] = 'e0daecb94db3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add image_source_stats table for tracking source performance."""
    op.create_table(
        'image_source_stats',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('source_name', sa.String(50), nullable=False),
        sa.Column('total_requests', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('successful_requests', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('failed_requests', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('avg_response_time_ms', sa.Float(), nullable=True),
        sa.Column('avg_quality_score', sa.Float(), nullable=True),
        sa.Column('priority_score', sa.Float(), nullable=True),
        sa.Column('last_used', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('source_name')
    )
    op.create_index(op.f('ix_image_source_stats_id'), 'image_source_stats', ['id'], unique=False)
    op.create_index(op.f('ix_image_source_stats_priority_score'), 'image_source_stats', ['priority_score'], unique=False)

    # Initialize with known sources
    from sqlalchemy import table, column
    from datetime import datetime

    image_source_stats = table('image_source_stats',
        column('source_name', sa.String),
        column('total_requests', sa.Integer),
        column('successful_requests', sa.Integer),
        column('failed_requests', sa.Integer),
        column('priority_score', sa.Float),
        column('created_at', sa.DateTime),
        column('updated_at', sa.DateTime)
    )

    now = datetime.utcnow()
    op.bulk_insert(image_source_stats, [
        {'source_name': 'sdss', 'total_requests': 0, 'successful_requests': 0, 'failed_requests': 0, 'priority_score': 100.0, 'created_at': now, 'updated_at': now},
        {'source_name': 'panstarrs', 'total_requests': 0, 'successful_requests': 0, 'failed_requests': 0, 'priority_score': 90.0, 'created_at': now, 'updated_at': now},
        {'source_name': 'skyview_dss', 'total_requests': 0, 'successful_requests': 0, 'failed_requests': 0, 'priority_score': 80.0, 'created_at': now, 'updated_at': now},
        {'source_name': 'eso', 'total_requests': 0, 'successful_requests': 0, 'failed_requests': 0, 'priority_score': 85.0, 'created_at': now, 'updated_at': now},
    ])


def downgrade() -> None:
    """Remove image_source_stats table."""
    op.drop_index(op.f('ix_image_source_stats_priority_score'), table_name='image_source_stats')
    op.drop_index(op.f('ix_image_source_stats_id'), table_name='image_source_stats')
    op.drop_table('image_source_stats')
