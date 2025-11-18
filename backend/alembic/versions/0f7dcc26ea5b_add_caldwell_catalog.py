"""add_caldwell_catalog

Revision ID: 0f7dcc26ea5b
Revises: 7c043c79d64c
Create Date: 2025-11-18 06:30:35.434335

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = '0f7dcc26ea5b'
down_revision: Union[str, Sequence[str], None] = '7c043c79d64c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - add caldwell_number column and import Caldwell catalog data."""
    # Add caldwell_number column to dso_catalog table
    op.add_column('dso_catalog', sa.Column('caldwell_number', sa.Integer(), nullable=True))

    # Create index on caldwell_number for efficient lookups
    op.create_index('ix_dso_catalog_caldwell_number', 'dso_catalog', ['caldwell_number'], unique=False)

    # Import Caldwell catalog data
    from scripts.caldwell_data import CALDWELL_CATALOG

    conn = op.get_bind()

    for obj in CALDWELL_CATALOG:
        # Parse NGC/IC designation
        ngc_ic = obj['ngc'].replace('NGC ', '').replace('IC ', '')
        catalog_name = 'NGC' if 'NGC' in obj['ngc'] else 'IC'

        # Handle special cases like NGC 869/884 (Double Cluster) or NGC 2237-9 (Rosette)
        if '/' in ngc_ic:
            catalog_number = int(ngc_ic.split('/')[0])
        elif '-' in ngc_ic:
            catalog_number = int(ngc_ic.split('-')[0])
        else:
            catalog_number = int(ngc_ic)

        # Check if object already exists (from Messier import or other sources)
        result = conn.execute(
            text("SELECT id FROM dso_catalog WHERE catalog_name = :cat_name AND catalog_number = :cat_num"),
            {"cat_name": catalog_name, "cat_num": catalog_number}
        ).fetchone()

        if result:
            # Update existing object with Caldwell number, common name, and object type
            conn.execute(
                text("""
                    UPDATE dso_catalog
                    SET caldwell_number = :caldwell_num,
                        common_name = COALESCE(:common_name, common_name),
                        object_type = :obj_type
                    WHERE catalog_name = :cat_name AND catalog_number = :cat_num
                """),
                {
                    "caldwell_num": obj['caldwell'],
                    "common_name": obj['common_name'],
                    "obj_type": obj['type'],
                    "cat_name": catalog_name,
                    "cat_num": catalog_number
                }
            )
        else:
            # Insert new Caldwell object
            conn.execute(
                text("""
                    INSERT INTO dso_catalog (
                        catalog_name, catalog_number, caldwell_number, common_name,
                        ra_hours, dec_degrees, object_type, magnitude,
                        size_major_arcmin, constellation
                    ) VALUES (
                        :cat_name, :cat_num, :caldwell_num, :common_name,
                        :ra_hours, :dec_degrees, :obj_type, :magnitude,
                        :size_arcmin, :constellation
                    )
                """),
                {
                    "cat_name": catalog_name,
                    "cat_num": catalog_number,
                    "caldwell_num": obj['caldwell'],
                    "common_name": obj['common_name'],
                    "ra_hours": obj['ra_hours'],
                    "dec_degrees": obj['dec_degrees'],
                    "obj_type": obj['type'],
                    "magnitude": obj['magnitude'],
                    "size_arcmin": obj['size_arcmin'],
                    "constellation": obj['constellation']
                }
            )


def downgrade() -> None:
    """Downgrade schema - remove caldwell_number column."""
    # Drop index
    op.drop_index('ix_dso_catalog_caldwell_number', table_name='dso_catalog')

    # Remove caldwell_number column
    op.drop_column('dso_catalog', 'caldwell_number')
