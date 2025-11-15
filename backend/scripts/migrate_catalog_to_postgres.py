#!/usr/bin/env python3
"""Migrate catalog data from SQLite to PostgreSQL."""

import sqlite3
import sys
from pathlib import Path

# Add parent directory to path so we can import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.catalog_models import DSOCatalog, CometCatalog, ConstellationName


def migrate_dso_catalog(sqlite_conn, pg_session: Session):
    """Migrate DSO catalog from SQLite to PostgreSQL."""
    cursor = sqlite_conn.cursor()

    # Get all DSO records
    cursor.execute("""
        SELECT id, catalog_name, catalog_number, common_name,
               ra_hours, dec_degrees, object_type, magnitude,
               surface_brightness, size_major_arcmin, size_minor_arcmin,
               constellation, created_at, updated_at
        FROM dso_catalog
    """)

    rows = cursor.fetchall()
    print(f"Found {len(rows)} DSO records in SQLite")

    # Insert into PostgreSQL
    count = 0
    for row in rows:
        dso = DSOCatalog(
            id=row[0],
            catalog_name=row[1],
            catalog_number=row[2],
            common_name=row[3],
            ra_hours=row[4],
            dec_degrees=row[5],
            object_type=row[6],
            magnitude=row[7],
            surface_brightness=row[8],
            size_major_arcmin=row[9],
            size_minor_arcmin=row[10],
            constellation=row[11],
            created_at=row[12],
            updated_at=row[13]
        )
        pg_session.add(dso)
        count += 1

        if count % 1000 == 0:
            print(f"  Migrated {count} DSO records...")
            pg_session.commit()

    pg_session.commit()
    print(f"✓ Migrated {count} DSO records")

    return count


def migrate_comet_catalog(sqlite_conn, pg_session: Session):
    """Migrate comet catalog from SQLite to PostgreSQL."""
    cursor = sqlite_conn.cursor()

    # Check if table exists
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='comet_catalog'
    """)

    if not cursor.fetchone():
        print("! Comet catalog table doesn't exist in SQLite, skipping")
        return 0

    # Get all comet records
    cursor.execute("""
        SELECT id, designation, name, discovery_date,
               epoch_jd, perihelion_distance_au, eccentricity,
               inclination_deg, arg_perihelion_deg, ascending_node_deg,
               perihelion_time_jd, absolute_magnitude, magnitude_slope,
               current_magnitude, activity_status, comet_type, data_source, notes
        FROM comet_catalog
    """)

    rows = cursor.fetchall()
    print(f"Found {len(rows)} comet records in SQLite")

    # Insert into PostgreSQL
    count = 0
    for row in rows:
        comet = CometCatalog(
            id=row[0],
            designation=row[1],
            name=row[2],
            discovery_date=row[3],
            epoch_jd=row[4],
            perihelion_distance_au=row[5],
            eccentricity=row[6],
            inclination_deg=row[7],
            arg_perihelion_deg=row[8],
            ascending_node_deg=row[9],
            perihelion_time_jd=row[10],
            absolute_magnitude=row[11],
            magnitude_slope=row[12],
            current_magnitude=row[13],
            activity_status=row[14],
            comet_type=row[15],
            data_source=row[16],
            notes=row[17]
        )
        pg_session.add(comet)
        count += 1

    pg_session.commit()
    print(f"✓ Migrated {count} comet records")

    return count


def migrate_constellation_names(sqlite_conn, pg_session: Session):
    """Migrate constellation names from SQLite to PostgreSQL."""
    cursor = sqlite_conn.cursor()

    # Check if table exists
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='constellation_names'
    """)

    if not cursor.fetchone():
        print("! Constellation names table doesn't exist in SQLite, skipping")
        return 0

    # Get all constellation records
    cursor.execute("""
        SELECT abbreviation, full_name
        FROM constellation_names
    """)

    rows = cursor.fetchall()
    print(f"Found {len(rows)} constellation records in SQLite")

    # Insert into PostgreSQL
    count = 0
    for row in rows:
        constellation = ConstellationName(
            abbreviation=row[0],
            full_name=row[1]
        )
        pg_session.add(constellation)
        count += 1

    pg_session.commit()
    print(f"✓ Migrated {count} constellation records")

    return count


def main():
    """Main migration function."""
    # Default SQLite database path
    sqlite_path = Path(__file__).parent.parent / "data" / "catalogs.db"

    if not sqlite_path.exists():
        print(f"Error: SQLite database not found at {sqlite_path}")
        sys.exit(1)

    print(f"Migrating catalog data from {sqlite_path}")
    print(f"To PostgreSQL (using DATABASE_URL from config)")
    print()

    # Connect to SQLite
    sqlite_conn = sqlite3.connect(str(sqlite_path))

    # Connect to PostgreSQL
    pg_session = SessionLocal()

    try:
        # Check if data already exists
        existing_dso = pg_session.query(DSOCatalog).count()
        existing_comets = pg_session.query(CometCatalog).count()

        if existing_dso > 0 or existing_comets > 0:
            print(f"Warning: PostgreSQL already has {existing_dso} DSO and {existing_comets} comet records")
            response = input("Continue and add more data? (y/N): ")
            if response.lower() != 'y':
                print("Migration cancelled")
                return

        # Migrate all tables
        dso_count = migrate_dso_catalog(sqlite_conn, pg_session)
        comet_count = migrate_comet_catalog(sqlite_conn, pg_session)
        const_count = migrate_constellation_names(sqlite_conn, pg_session)

        print()
        print("=" * 60)
        print("Migration complete!")
        print(f"  DSO records: {dso_count}")
        print(f"  Comet records: {comet_count}")
        print(f"  Constellation records: {const_count}")
        print("=" * 60)

    except Exception as e:
        print(f"\nError during migration: {e}")
        pg_session.rollback()
        raise

    finally:
        sqlite_conn.close()
        pg_session.close()


if __name__ == "__main__":
    main()
