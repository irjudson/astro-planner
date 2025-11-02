#!/usr/bin/env python3
"""
Initialize test database with schema and sample data.

This is a lightweight alternative to import_catalog.py for CI/testing.
Creates the database schema and adds a few sample objects.
"""

import sqlite3
import sys
from pathlib import Path

def get_database_path():
    """Get database path based on environment."""
    docker_path = Path("/app/data/catalogs.db")
    local_path = Path("backend/data/catalogs.db")

    # Use docker path if it exists, otherwise use local path
    if docker_path.parent.exists():
        return str(docker_path)
    return str(local_path)


def create_test_database():
    """Create database schema and add sample test data."""
    db_path = get_database_path()
    print(f"Creating test database at: {db_path}")

    # Ensure directory exists
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create DSO catalog table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dso_catalog (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            catalog_name VARCHAR(20),
            catalog_number VARCHAR(20),
            common_name VARCHAR(100),
            ra_hours FLOAT NOT NULL,
            dec_degrees FLOAT NOT NULL,
            object_type VARCHAR(50),
            magnitude FLOAT,
            surface_brightness FLOAT,
            size_major_arcmin FLOAT,
            size_minor_arcmin FLOAT,
            constellation VARCHAR(20),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            UNIQUE(catalog_name, catalog_number)
        )
    """)

    # Add sample test objects (without description - it's generated dynamically)
    test_objects = [
        ('NGC', '31', 'Andromeda Galaxy', 0.712, 41.269, 'galaxy', 3.4, 13.5, 178.0, 63.0, 'And'),
        ('NGC', '224', 'Andromeda Galaxy', 0.712, 41.269, 'galaxy', 3.4, 13.5, 178.0, 63.0, 'And'),
        ('NGC', '598', 'Triangulum Galaxy', 1.564, 30.660, 'galaxy', 5.7, 14.2, 68.7, 41.6, 'Tri'),
        ('NGC', '5194', 'Whirlpool Galaxy', 13.498, 47.195, 'galaxy', 8.4, 13.0, 11.2, 6.9, 'CVn'),
        ('NGC', '5272', 'M3', 13.703, 28.377, 'globular_cluster', 6.2, 11.0, 18.0, 18.0, 'CVn'),
        ('NGC', '6720', 'Ring Nebula', 18.897, 33.029, 'planetary_nebula', 8.8, 9.7, 1.4, 1.0, 'Lyr'),
        ('NGC', '6853', 'Dumbbell Nebula', 19.993, 22.721, 'planetary_nebula', 7.5, 9.9, 8.0, 5.6, 'Vul'),
        ('NGC', '7078', 'M15', 21.499, 12.167, 'globular_cluster', 6.2, 11.0, 18.0, 18.0, 'Peg'),
        ('NGC', '7089', 'M2', 21.558, -0.823, 'globular_cluster', 6.3, 11.0, 16.0, 16.0, 'Aqr'),
        ('IC', '1613', None, 1.079, 2.133, 'galaxy', 9.2, 14.5, 16.2, 14.5, 'Cet'),
    ]

    cursor.executemany("""
        INSERT OR IGNORE INTO dso_catalog
        (catalog_name, catalog_number, common_name, ra_hours, dec_degrees,
         object_type, magnitude, surface_brightness, size_major_arcmin,
         size_minor_arcmin, constellation)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, test_objects)

    conn.commit()

    # Verify
    cursor.execute("SELECT COUNT(*) FROM dso_catalog")
    count = cursor.fetchone()[0]
    print(f"✓ Created database with {count} sample objects")

    conn.close()
    print("✓ Test database initialized successfully")


if __name__ == "__main__":
    try:
        create_test_database()
        sys.exit(0)
    except Exception as e:
        print(f"Error creating test database: {e}")
        sys.exit(1)
