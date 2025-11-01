#!/usr/bin/env python3
"""
Import OpenNGC catalog into SQLite database.

This script creates the database schema and imports all NGC and IC objects
from the pyongc library into a SQLite database for the astro planner.
"""

import sqlite3
import sys
import math
from pathlib import Path
from typing import Optional

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from pyongc import Dso, ObjectNotFound
except ImportError:
    print("Error: pyongc not installed. Run: pip install pyongc")
    sys.exit(1)


def create_database_schema(conn: sqlite3.Connection) -> None:
    """Create the database schema for DSO catalog."""
    cursor = conn.cursor()

    # Main DSO catalog table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dso_catalog (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            catalog_name VARCHAR(20),        -- 'NGC', 'IC', 'Messier'
            catalog_number VARCHAR(20),      -- '31', '224', etc.
            common_name VARCHAR(100),        -- 'Andromeda Galaxy'

            -- Coordinates (J2000)
            ra_hours FLOAT NOT NULL,
            dec_degrees FLOAT NOT NULL,

            -- Physical properties
            object_type VARCHAR(50),         -- galaxy, nebula, cluster, etc.
            magnitude FLOAT,                 -- Visual magnitude
            surface_brightness FLOAT,        -- mag/arcsec^2
            size_major_arcmin FLOAT,         -- Major axis in arcminutes
            size_minor_arcmin FLOAT,         -- Minor axis in arcminutes

            -- Observing info
            constellation VARCHAR(20),

            -- Metadata
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            -- Ensure uniqueness
            UNIQUE(catalog_name, catalog_number)
        )
    """)

    # Create indexes for fast queries
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_object_type
        ON dso_catalog(object_type)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_magnitude
        ON dso_catalog(magnitude)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_coords
        ON dso_catalog(ra_hours, dec_degrees)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_constellation
        ON dso_catalog(constellation)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_catalog_lookup
        ON dso_catalog(catalog_name, catalog_number)
    """)

    # Constellation names lookup table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS constellation_names (
            abbreviation VARCHAR(10) PRIMARY KEY,
            full_name VARCHAR(50) NOT NULL
        )
    """)

    conn.commit()
    print("✅ Database schema created successfully")


def populate_constellation_names(conn: sqlite3.Connection) -> None:
    """Populate the constellation names lookup table."""
    cursor = conn.cursor()

    constellations = {
        "And": "Andromeda", "Ant": "Antlia", "Aps": "Apus", "Aqr": "Aquarius",
        "Aql": "Aquila", "Ara": "Ara", "Ari": "Aries", "Aur": "Auriga",
        "Boo": "Boötes", "Cae": "Caelum", "Cam": "Camelopardalis", "Cnc": "Cancer",
        "CVn": "Canes Venatici", "CMa": "Canis Major", "CMi": "Canis Minor",
        "Cap": "Capricornus", "Car": "Carina", "Cas": "Cassiopeia", "Cen": "Centaurus",
        "Cep": "Cepheus", "Cet": "Cetus", "Cha": "Chamaeleon", "Cir": "Circinus",
        "Col": "Columba", "Com": "Coma Berenices", "CrA": "Corona Australis",
        "CrB": "Corona Borealis", "Crv": "Corvus", "Crt": "Crater", "Cru": "Crux",
        "Cyg": "Cygnus", "Del": "Delphinus", "Dor": "Dorado", "Dra": "Draco",
        "Equ": "Equuleus", "Eri": "Eridanus", "For": "Fornax", "Gem": "Gemini",
        "Gru": "Grus", "Her": "Hercules", "Hor": "Horologium", "Hya": "Hydra",
        "Hyi": "Hydrus", "Ind": "Indus", "Lac": "Lacerta", "Leo": "Leo",
        "LMi": "Leo Minor", "Lep": "Lepus", "Lib": "Libra", "Lup": "Lupus",
        "Lyn": "Lynx", "Lyr": "Lyra", "Men": "Mensa", "Mic": "Microscopium",
        "Mon": "Monoceros", "Mus": "Musca", "Nor": "Norma", "Oct": "Octans",
        "Oph": "Ophiuchus", "Ori": "Orion", "Pav": "Pavo", "Peg": "Pegasus",
        "Per": "Perseus", "Phe": "Phoenix", "Pic": "Pictor", "Psc": "Pisces",
        "PsA": "Piscis Austrinus", "Pup": "Puppis", "Pyx": "Pyxis", "Ret": "Reticulum",
        "Sge": "Sagitta", "Sgr": "Sagittarius", "Sco": "Scorpius", "Scl": "Sculptor",
        "Sct": "Scutum", "Ser": "Serpens", "Sex": "Sextans", "Tau": "Taurus",
        "Tel": "Telescopium", "Tri": "Triangulum", "TrA": "Triangulum Australe",
        "Tuc": "Tucana", "UMa": "Ursa Major", "UMi": "Ursa Minor", "Vel": "Vela",
        "Vir": "Virgo", "Vol": "Volans", "Vul": "Vulpecula"
    }

    for abbr, full in constellations.items():
        cursor.execute("""
            INSERT OR IGNORE INTO constellation_names (abbreviation, full_name)
            VALUES (?, ?)
        """, (abbr, full))

    conn.commit()
    print(f"✅ Populated {len(constellations)} constellation names")


def map_object_type(ongc_type: str) -> str:
    """Map OpenNGC object types to our standard types."""
    # pyongc returns nice type strings like "Galaxy", "Nebula", etc.
    # Just normalize to lowercase
    if not ongc_type:
        return 'other'

    type_lower = ongc_type.lower().strip()

    # Map variations to standard types
    type_mapping = {
        'galaxy': 'galaxy',
        'open cluster': 'cluster',
        'globular cluster': 'cluster',
        'cluster': 'cluster',
        'planetary nebula': 'planetary_nebula',
        'nebula': 'nebula',
        'emission nebula': 'nebula',
        'reflection nebula': 'nebula',
        'supernova remnant': 'nebula',
        'h ii region': 'nebula',
        'star': 'star',
        'double star': 'star',
        'nonexistent': 'nonexistent',
        'duplicate': 'duplicate',
    }

    return type_mapping.get(type_lower, 'other')


def import_ngc_objects(conn: sqlite3.Connection, limit: Optional[int] = None) -> int:
    """Import NGC catalog objects."""
    cursor = conn.cursor()
    imported = 0
    skipped = 0

    print(f"Importing NGC catalog...")

    # NGC catalog: 1 to 7840
    for ngc_num in range(1, 7841):
        if limit and imported >= limit:
            break

        try:
            obj = Dso(f"NGC{ngc_num}")

            # Skip nonexistent and duplicate entries
            obj_type = map_object_type(obj.type)
            if obj_type in ['nonexistent', 'duplicate', 'star']:
                skipped += 1
                continue

            # Get coordinates in radians, convert to hours and degrees
            try:
                rad_coords = obj.rad_coords  # Returns [ra_radians, dec_radians]
                ra = float(rad_coords[0]) * 12.0 / math.pi  # Convert radians to hours
                dec = float(rad_coords[1]) * 180.0 / math.pi  # Convert radians to degrees
            except (TypeError, IndexError, ValueError, AttributeError):
                skipped += 1
                continue

            # Get dimensions (returns numpy array or tuple)
            size_major = None
            size_minor = None
            try:
                if obj.dimensions is not None and len(obj.dimensions) >= 2:
                    size_major = float(obj.dimensions[0]) if obj.dimensions[0] else None
                    size_minor = float(obj.dimensions[1]) if obj.dimensions[1] else None
            except (TypeError, ValueError):
                pass

            # Get common names from identifiers
            common_name = None
            try:
                identifiers = list(obj.identifiers) if obj.identifiers is not None else []
            except (TypeError, AttributeError):
                identifiers = []
            if identifiers:
                # Look for common names (not just catalog IDs)
                for ident in identifiers:
                    if ident and isinstance(ident, str) and not any(x in ident for x in ['NGC', 'IC', 'UGC', 'PGC', 'ESO']):
                        common_name = ident
                        break

            # Check if it's a Messier object
            is_messier = 'M' in identifiers if identifiers else False
            messier_num = None
            if is_messier:
                for ident in identifiers:
                    if ident.startswith('M') and ident[1:].isdigit():
                        messier_num = ident[1:]
                        break

            # Get magnitude (can be dict, tuple, float, or None)
            magnitude = None
            try:
                if obj.magnitudes:
                    if isinstance(obj.magnitudes, dict):
                        magnitude = obj.magnitudes.get('V') or obj.magnitudes.get('B')
                    elif isinstance(obj.magnitudes, (tuple, list)):
                        # Sometimes magnitudes is a tuple, take first value
                        magnitude = float(obj.magnitudes[0]) if obj.magnitudes[0] is not None else None
                    else:
                        magnitude = float(obj.magnitudes)
            except (TypeError, ValueError, IndexError):
                magnitude = None

            cursor.execute("""
                INSERT OR IGNORE INTO dso_catalog (
                    catalog_name, catalog_number, common_name,
                    ra_hours, dec_degrees,
                    object_type, magnitude, surface_brightness,
                    size_major_arcmin, size_minor_arcmin,
                    constellation
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                'Messier' if is_messier else 'NGC',
                messier_num if is_messier else str(ngc_num),
                common_name,
                ra,  # RA in hours
                dec,  # Dec in degrees
                obj_type,
                magnitude,
                float(obj.surface_brightness) if obj.surface_brightness else None,
                size_major,
                size_minor,
                obj.constellation if obj.constellation else None
            ))

            imported += 1

            if imported % 500 == 0:
                conn.commit()
                print(f"  Imported {imported} NGC objects...")

        except ObjectNotFound:
            # Object doesn't exist in catalog
            skipped += 1
        except Exception as e:
            # Other error
            skipped += 1
            if imported < 10:  # Show first few errors for debugging
                print(f"  Error on NGC{ngc_num}: {e}")
            continue

    conn.commit()
    print(f"✅ NGC catalog complete: {imported} imported, {skipped} skipped")
    return imported


def import_ic_objects(conn: sqlite3.Connection, limit: Optional[int] = None) -> int:
    """Import IC catalog objects."""
    cursor = conn.cursor()
    imported = 0
    skipped = 0

    print(f"Importing IC catalog...")

    # IC catalog: 1 to 5386
    for ic_num in range(1, 5387):
        if limit and imported >= limit:
            break

        try:
            obj = Dso(f"IC{ic_num}")

            # Skip nonexistent and duplicate entries
            obj_type = map_object_type(obj.type)
            if obj_type in ['nonexistent', 'duplicate', 'star']:
                skipped += 1
                continue

            # Get coordinates in radians, convert to hours and degrees
            try:
                rad_coords = obj.rad_coords  # Returns [ra_radians, dec_radians]
                ra = float(rad_coords[0]) * 12.0 / math.pi  # Convert radians to hours
                dec = float(rad_coords[1]) * 180.0 / math.pi  # Convert radians to degrees
            except (TypeError, IndexError, ValueError, AttributeError):
                skipped += 1
                continue

            # Get dimensions (returns numpy array or tuple)
            size_major = None
            size_minor = None
            try:
                if obj.dimensions is not None and len(obj.dimensions) >= 2:
                    size_major = float(obj.dimensions[0]) if obj.dimensions[0] else None
                    size_minor = float(obj.dimensions[1]) if obj.dimensions[1] else None
            except (TypeError, ValueError):
                pass

            # Get common names from identifiers
            common_name = None
            try:
                identifiers = list(obj.identifiers) if obj.identifiers is not None else []
            except (TypeError, AttributeError):
                identifiers = []
            if identifiers:
                for ident in identifiers:
                    if ident and isinstance(ident, str) and not any(x in ident for x in ['NGC', 'IC', 'UGC', 'PGC', 'ESO']):
                        common_name = ident
                        break

            # Get magnitude (can be dict, tuple, float, or None)
            magnitude = None
            try:
                if obj.magnitudes:
                    if isinstance(obj.magnitudes, dict):
                        magnitude = obj.magnitudes.get('V') or obj.magnitudes.get('B')
                    elif isinstance(obj.magnitudes, (tuple, list)):
                        # Sometimes magnitudes is a tuple, take first value
                        magnitude = float(obj.magnitudes[0]) if obj.magnitudes[0] is not None else None
                    else:
                        magnitude = float(obj.magnitudes)
            except (TypeError, ValueError, IndexError):
                magnitude = None

            cursor.execute("""
                INSERT OR IGNORE INTO dso_catalog (
                    catalog_name, catalog_number, common_name,
                    ra_hours, dec_degrees,
                    object_type, magnitude, surface_brightness,
                    size_major_arcmin, size_minor_arcmin,
                    constellation
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                'IC',
                str(ic_num),
                common_name,
                ra,  # RA in hours
                dec,  # Dec in degrees
                obj_type,
                magnitude,
                float(obj.surface_brightness) if obj.surface_brightness else None,
                size_major,
                size_minor,
                obj.constellation if obj.constellation else None
            ))

            imported += 1

            if imported % 500 == 0:
                conn.commit()
                print(f"  Imported {imported} IC objects...")

        except ObjectNotFound:
            skipped += 1
        except Exception as e:
            skipped += 1
            if imported < 10:  # Show first few errors for debugging
                print(f"  Error on IC{ic_num}: {e}")
            continue

    conn.commit()
    print(f"✅ IC catalog complete: {imported} imported, {skipped} skipped")
    return imported


def print_statistics(conn: sqlite3.Connection) -> None:
    """Print statistics about the imported catalog."""
    cursor = conn.cursor()

    # Total count
    cursor.execute("SELECT COUNT(*) FROM dso_catalog")
    total = cursor.fetchone()[0]

    # Count by catalog
    cursor.execute("""
        SELECT catalog_name, COUNT(*)
        FROM dso_catalog
        GROUP BY catalog_name
        ORDER BY COUNT(*) DESC
    """)
    by_catalog = cursor.fetchall()

    # Count by object type
    cursor.execute("""
        SELECT object_type, COUNT(*)
        FROM dso_catalog
        GROUP BY object_type
        ORDER BY COUNT(*) DESC
    """)
    by_type = cursor.fetchall()

    print("\n" + "="*50)
    print("DATABASE STATISTICS")
    print("="*50)
    print(f"Total objects: {total}")
    print("\nBy catalog:")
    for catalog, count in by_catalog:
        print(f"  {catalog}: {count}")
    print("\nBy object type:")
    for obj_type, count in by_type:
        print(f"  {obj_type}: {count}")
    print("="*50)


def main():
    """Main import function."""
    import argparse

    parser = argparse.ArgumentParser(description='Import OpenNGC catalog to SQLite')
    parser.add_argument(
        '--database',
        default='backend/data/catalogs.db',
        help='Path to SQLite database file (default: backend/data/catalogs.db)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='Limit number of objects to import (for testing)'
    )
    parser.add_argument(
        '--rebuild',
        action='store_true',
        help='Drop existing tables and rebuild from scratch'
    )

    args = parser.parse_args()

    # Ensure data directory exists
    db_path = Path(args.database)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"📚 OpenNGC Catalog Import")
    print(f"Database: {db_path}")
    print()

    # Connect to database
    conn = sqlite3.connect(str(db_path))

    if args.rebuild:
        print("⚠️  Rebuilding database (dropping existing tables)...")
        cursor = conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS dso_catalog")
        cursor.execute("DROP TABLE IF EXISTS constellation_names")
        conn.commit()

    # Create schema
    create_database_schema(conn)

    # Populate constellation names
    populate_constellation_names(conn)

    # Import catalogs
    ngc_count = import_ngc_objects(conn, limit=args.limit)
    ic_count = import_ic_objects(conn, limit=args.limit)

    # Print statistics
    print_statistics(conn)

    conn.close()

    print(f"\n✅ Import complete!")
    print(f"   NGC objects: {ngc_count}")
    print(f"   IC objects: {ic_count}")
    print(f"   Total: {ngc_count + ic_count}")
    print(f"   Database: {db_path}")


if __name__ == '__main__':
    main()
