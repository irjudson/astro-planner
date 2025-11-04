#!/usr/bin/env python3
"""Create asteroid catalog tables in the database."""

import sqlite3
from pathlib import Path

def create_asteroid_tables():
    """Create tables for asteroid catalog."""
    # Auto-detect database path
    docker_path = Path("/app/data/catalogs.db")
    local_path = Path("backend/data/catalogs.db")

    if docker_path.exists():
        db_path = docker_path
    else:
        db_path = local_path
        db_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Using database: {db_path}")

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Create asteroid_catalog table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS asteroid_catalog (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            designation VARCHAR(50) NOT NULL UNIQUE,
            name VARCHAR(100),
            number INTEGER,
            discovery_date DATE,
            epoch_jd FLOAT NOT NULL,
            perihelion_distance_au FLOAT NOT NULL,
            eccentricity FLOAT NOT NULL,
            inclination_deg FLOAT NOT NULL,
            arg_perihelion_deg FLOAT NOT NULL,
            ascending_node_deg FLOAT NOT NULL,
            mean_anomaly_deg FLOAT NOT NULL,
            semi_major_axis_au FLOAT NOT NULL,
            absolute_magnitude FLOAT,
            slope_parameter FLOAT DEFAULT 0.15,
            current_magnitude FLOAT,
            diameter_km FLOAT,
            albedo FLOAT,
            spectral_type VARCHAR(10),
            rotation_period_hours FLOAT,
            asteroid_type VARCHAR(20),
            data_source VARCHAR(50),
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create asteroid_ephemeris table for caching computed positions
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS asteroid_ephemeris (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            asteroid_id INTEGER NOT NULL,
            date_jd FLOAT NOT NULL,
            date_utc TIMESTAMP NOT NULL,
            helio_distance_au FLOAT NOT NULL,
            geo_distance_au FLOAT,
            ra_hours FLOAT NOT NULL,
            dec_degrees FLOAT NOT NULL,
            magnitude FLOAT,
            elongation_deg FLOAT,
            phase_angle_deg FLOAT,
            FOREIGN KEY (asteroid_id) REFERENCES asteroid_catalog(id),
            UNIQUE(asteroid_id, date_jd)
        )
    """)

    # Create indexes for better query performance
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_asteroid_magnitude
        ON asteroid_catalog(current_magnitude)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_asteroid_type
        ON asteroid_catalog(asteroid_type)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_asteroid_number
        ON asteroid_catalog(number)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_asteroid_ephemeris_date
        ON asteroid_ephemeris(date_jd)
    """)

    conn.commit()

    # Check table creation
    cursor.execute("""
        SELECT COUNT(*) FROM asteroid_catalog
    """)
    count = cursor.fetchone()[0]

    print(f"✓ Created asteroid_catalog table ({count} asteroids)")

    cursor.execute("""
        SELECT COUNT(*) FROM asteroid_ephemeris
    """)
    count = cursor.fetchone()[0]

    print(f"✓ Created asteroid_ephemeris table ({count} cached ephemerides)")

    conn.close()
    print("\n✓ Asteroid tables created successfully!")

if __name__ == "__main__":
    create_asteroid_tables()
