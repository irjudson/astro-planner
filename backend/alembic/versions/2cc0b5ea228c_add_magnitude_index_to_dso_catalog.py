"""add_magnitude_index_to_dso_catalog

Revision ID: 2cc0b5ea228c
Revises: a8b2c3d4e5f6
Create Date: 2025-12-27 16:28:46.416181

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2cc0b5ea228c'
down_revision: Union[str, Sequence[str], None] = 'a8b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add index on magnitude column for faster sorting."""
    op.create_index(
        'idx_dso_catalog_magnitude',
        'dso_catalog',
        ['magnitude'],
        unique=False
    )


def downgrade() -> None:
    """Remove magnitude index."""
    op.drop_index('idx_dso_catalog_magnitude', table_name='dso_catalog')
