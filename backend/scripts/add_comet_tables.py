#!/usr/bin/env python3
"""
Add comet tables to the astronomy database.

This script adds tables for storing comet orbital elements and ephemerides.
"""

import sqlite3
import sys
from pathlib import Path


def get_database_path():
    """Get database path based on environment."""
    docker_path = Path("/app/data/catalogs.db")
    local_path = Path("backend/data/catalogs.db")
    data_path = Path("data/catalogs.db")

    # Try paths in order
    for path in [docker_path, local_path, data_path]:
        if path.exists():
            return str(path)

    # Default to local path if none exist yet
    return str(local_path)


def add_comet_tables():
    """Add comet catalog and ephemeris tables to the database."""
    db_path = get_database_path()
    print(f"Adding comet tables to database at: {db_path}")

    # Ensure directory exists
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create comet catalog table with orbital elements
    # Using standard Keplerian orbital elements
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS comet_catalog (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            -- Identification
            designation VARCHAR(50) NOT NULL UNIQUE,  -- Official designation (e.g., "C/2020 F3")
            name VARCHAR(100),                         -- Common name (e.g., "NEOWISE")
            discovery_date DATE,                       -- Discovery date

            -- Orbital Elements (Keplerian)
            -- Epoch of elements (Julian Date)
            epoch_jd FLOAT NOT NULL,

            -- Perihelion distance in AU
            perihelion_distance_au FLOAT NOT NULL,

            -- Eccentricity (0 = circular, 0-1 = elliptical, >1 = hyperbolic)
            eccentricity FLOAT NOT NULL,

            -- Inclination in degrees (orbital plane tilt relative to ecliptic)
            inclination_deg FLOAT NOT NULL,

            -- Argument of perihelion in degrees (ω)
            arg_perihelion_deg FLOAT NOT NULL,

            -- Longitude of ascending node in degrees (Ω)
            ascending_node_deg FLOAT NOT NULL,

            -- Time of perihelion passage (Julian Date)
            perihelion_time_jd FLOAT NOT NULL,

            -- Physical Parameters
            -- Absolute magnitude (brightness at 1 AU from Sun and Earth)
            absolute_magnitude FLOAT,

            -- Magnitude slope parameter (typically 4.0 for most comets)
            magnitude_slope FLOAT DEFAULT 4.0,

            -- Nuclear magnitude (magnitude of nucleus alone)
            nuclear_magnitude FLOAT,

            -- Observability
            -- Current estimated magnitude (updated periodically)
            current_magnitude FLOAT,

            -- Activity status
            activity_status VARCHAR(20),  -- 'active', 'inactive', 'unknown'

            -- Classification
            -- Type: short-period (<20 yr), long-period (>20 yr), hyperbolic
            comet_type VARCHAR(20),

            -- Data source and metadata
            data_source VARCHAR(50),       -- 'MPC', 'JPL', 'manual'
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            -- Observing notes
            notes TEXT
        )
    """)

    # Create ephemeris cache table for pre-computed positions
    # This improves performance for visibility queries
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS comet_ephemeris (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            -- Link to comet
            comet_id INTEGER NOT NULL,

            -- Time of ephemeris
            date_jd FLOAT NOT NULL,           -- Julian Date
            date_utc TIMESTAMP NOT NULL,       -- UTC timestamp for easy querying

            -- Heliocentric coordinates (position relative to Sun)
            helio_distance_au FLOAT NOT NULL,  -- Distance from Sun in AU

            -- Geocentric coordinates (position relative to Earth)
            geo_distance_au FLOAT,             -- Distance from Earth in AU
            ra_hours FLOAT NOT NULL,           -- Right Ascension in hours
            dec_degrees FLOAT NOT NULL,        -- Declination in degrees

            -- Observability
            magnitude FLOAT,                   -- Estimated visual magnitude
            elongation_deg FLOAT,              -- Angular distance from Sun
            phase_angle_deg FLOAT,             -- Sun-comet-Earth angle

            -- Metadata
            computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            -- Indexes for fast queries
            FOREIGN KEY (comet_id) REFERENCES comet_catalog(id) ON DELETE CASCADE,
            UNIQUE(comet_id, date_jd)
        )
    """)

    # Create indexes for better query performance
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_comet_designation
        ON comet_catalog(designation)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_comet_name
        ON comet_catalog(name)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_comet_magnitude
        ON comet_catalog(current_magnitude)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_ephemeris_comet_date
        ON comet_ephemeris(comet_id, date_utc)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_ephemeris_date
        ON comet_ephemeris(date_utc)
    """)

    conn.commit()

    # Verify tables were created
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name LIKE 'comet%'
        ORDER BY name
    """)
    tables = cursor.fetchall()

    conn.close()

    print(f"✓ Created {len(tables)} comet tables:")
    for table in tables:
        print(f"  - {table[0]}")

    print("✓ Comet tables added successfully")


if __name__ == "__main__":
    try:
        add_comet_tables()
        sys.exit(0)
    except Exception as e:
        print(f"Error adding comet tables: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
