"""Remove processing sessions, simplify to direct file processing

Revision ID: f067834e5435
Revises: 79478a6f4f48
Create Date: 2025-11-15 14:12:26.599117

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'f067834e5435'
down_revision: Union[str, Sequence[str], None] = '79478a6f4f48'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Drop foreign keys first, before dropping the table
    op.drop_constraint('processing_files_session_id_fkey', 'processing_files', type_='foreignkey')
    op.drop_constraint('processing_jobs_session_id_fkey', 'processing_jobs', type_='foreignkey')

    # Drop columns
    op.drop_column('processing_files', 'session_id')
    op.drop_column('processing_jobs', 'session_id')

    # Add new file_id column and foreign key
    op.add_column('processing_jobs', sa.Column('file_id', sa.Integer(), nullable=False))
    op.create_foreign_key(None, 'processing_jobs', 'processing_files', ['file_id'], ['id'])

    # Now drop the sessions table
    op.drop_index('ix_processing_sessions_id', table_name='processing_sessions')
    op.drop_table('processing_sessions')


def downgrade() -> None:
    """Downgrade schema."""
    # Create processing_sessions table FIRST before adding foreign keys
    op.create_table('processing_sessions',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('user_id', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('session_name', sa.VARCHAR(length=100), autoincrement=False, nullable=False),
    sa.Column('observation_plan_id', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('upload_timestamp', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
    sa.Column('total_files', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('total_size_bytes', sa.BIGINT(), autoincrement=False, nullable=True),
    sa.Column('status', sa.VARCHAR(length=20), autoincrement=False, nullable=True),
    sa.Column('session_metadata', postgresql.JSON(astext_type=sa.Text()), autoincrement=False, nullable=True),
    sa.Column('created_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
    sa.PrimaryKeyConstraint('id', name='processing_sessions_pkey')
    )
    op.create_index('ix_processing_sessions_id', 'processing_sessions', ['id'], unique=False)

    # Now add session_id columns and foreign keys
    op.add_column('processing_files', sa.Column('session_id', sa.INTEGER(), autoincrement=False, nullable=False))
    op.create_foreign_key('processing_files_session_id_fkey', 'processing_files', 'processing_sessions', ['session_id'], ['id'])

    op.add_column('processing_jobs', sa.Column('session_id', sa.INTEGER(), autoincrement=False, nullable=False))
    op.drop_constraint('processing_jobs_file_id_fkey', 'processing_jobs', type_='foreignkey')
    op.create_foreign_key('processing_jobs_session_id_fkey', 'processing_jobs', 'processing_sessions', ['session_id'], ['id'])
    op.drop_column('processing_jobs', 'file_id')
