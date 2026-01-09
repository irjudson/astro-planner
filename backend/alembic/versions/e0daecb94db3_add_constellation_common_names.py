"""add_constellation_common_names

Revision ID: e0daecb94db3
Revises: c020a828cd8b
Create Date: 2026-01-04 23:00:40.737258

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e0daecb94db3'
down_revision: Union[str, Sequence[str], None] = 'c020a828cd8b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add common_name column to constellation_names table and populate with data."""
    # Add column
    op.add_column('constellation_names', sa.Column('common_name', sa.String(length=100), nullable=True))

    # Populate common names for all 88 constellations
    constellation_data = {
        'And': 'The Princess', 'Ant': 'The Air Pump', 'Aps': 'The Bird of Paradise',
        'Aqr': 'The Water Bearer', 'Aql': 'The Eagle', 'Ara': 'The Altar',
        'Ari': 'The Ram', 'Aur': 'The Charioteer', 'Boo': 'The Herdsman',
        'Cae': 'The Chisel', 'Cam': 'The Giraffe', 'Cnc': 'The Crab',
        'CVn': 'The Hunting Dogs', 'CMa': 'The Great Dog', 'CMi': 'The Little Dog',
        'Cap': 'The Sea Goat', 'Car': 'The Keel', 'Cas': 'The Queen',
        'Cen': 'The Centaur', 'Cep': 'The King', 'Cet': 'The Whale',
        'Cha': 'The Chameleon', 'Cir': 'The Compasses', 'Col': 'The Dove',
        'Com': 'Berenice\'s Hair', 'CrA': 'The Southern Crown', 'CrB': 'The Northern Crown',
        'Crv': 'The Crow', 'Crt': 'The Cup', 'Cru': 'The Southern Cross',
        'Cyg': 'The Swan', 'Del': 'The Dolphin', 'Dor': 'The Goldfish',
        'Dra': 'The Dragon', 'Equ': 'The Little Horse', 'Eri': 'The River',
        'For': 'The Furnace', 'Gem': 'The Twins', 'Gru': 'The Crane',
        'Her': 'The Hero', 'Hor': 'The Clock', 'Hya': 'The Water Snake',
        'Hyi': 'The Little Water Snake', 'Ind': 'The Indian', 'Lac': 'The Lizard',
        'Leo': 'The Lion', 'LMi': 'The Little Lion', 'Lep': 'The Hare',
        'Lib': 'The Scales', 'Lup': 'The Wolf', 'Lyn': 'The Lynx',
        'Lyr': 'The Lyre', 'Men': 'The Table Mountain', 'Mic': 'The Microscope',
        'Mon': 'The Unicorn', 'Mus': 'The Fly', 'Nor': 'The Carpenter\'s Square',
        'Oct': 'The Octant', 'Oph': 'The Serpent Bearer', 'Ori': 'The Hunter',
        'Pav': 'The Peacock', 'Peg': 'The Winged Horse', 'Per': 'The Hero',
        'Phe': 'The Phoenix', 'Pic': 'The Painter\'s Easel', 'Psc': 'The Fishes',
        'PsA': 'The Southern Fish', 'Pup': 'The Stern', 'Pyx': 'The Compass',
        'Ret': 'The Reticle', 'Sge': 'The Arrow', 'Sgr': 'The Archer',
        'Sco': 'The Scorpion', 'Scl': 'The Sculptor', 'Sct': 'The Shield',
        'Ser': 'The Serpent', 'Sex': 'The Sextant', 'Tau': 'The Bull',
        'Tel': 'The Telescope', 'Tri': 'The Triangle', 'TrA': 'The Southern Triangle',
        'Tuc': 'The Toucan', 'UMa': 'The Great Bear', 'UMi': 'The Little Bear',
        'Vel': 'The Sails', 'Vir': 'The Virgin', 'Vol': 'The Flying Fish',
        'Vul': 'The Fox'
    }

    # Update each constellation
    from sqlalchemy import table, column
    constellation_names = table('constellation_names',
        column('abbreviation', sa.String),
        column('common_name', sa.String)
    )

    for abbr, common in constellation_data.items():
        op.execute(
            constellation_names.update()
            .where(constellation_names.c.abbreviation == abbr)
            .values(common_name=common)
        )


def downgrade() -> None:
    """Remove common_name column from constellation_names table."""
    op.drop_column('constellation_names', 'common_name')
