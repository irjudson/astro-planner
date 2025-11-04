"""Pytest configuration and shared fixtures."""

import pytest
import sys
import tempfile
import sqlite3
from pathlib import Path

# Add app directory to Python path
app_dir = Path(__file__).parent.parent
sys.path.insert(0, str(app_dir))


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    # Create a temporary file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    db_path = temp_file.name
    temp_file.close()

    # Create the database schema
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create comet_catalog table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS comet_catalog (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            designation VARCHAR(50) NOT NULL UNIQUE,
            name VARCHAR(100),
            discovery_date DATE,
            epoch_jd FLOAT NOT NULL,
            perihelion_distance_au FLOAT NOT NULL,
            eccentricity FLOAT NOT NULL,
            inclination_deg FLOAT NOT NULL,
            arg_perihelion_deg FLOAT NOT NULL,
            ascending_node_deg FLOAT NOT NULL,
            perihelion_time_jd FLOAT NOT NULL,
            absolute_magnitude FLOAT,
            magnitude_slope FLOAT DEFAULT 4.0,
            current_magnitude FLOAT,
            activity_status VARCHAR(20),
            comet_type VARCHAR(20),
            data_source VARCHAR(50),
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create comet_ephemeris table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS comet_ephemeris (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            comet_id INTEGER NOT NULL,
            date_jd FLOAT NOT NULL,
            date_utc TIMESTAMP NOT NULL,
            helio_distance_au FLOAT NOT NULL,
            geo_distance_au FLOAT,
            ra_hours FLOAT NOT NULL,
            dec_degrees FLOAT NOT NULL,
            magnitude FLOAT,
            elongation_deg FLOAT,
            phase_angle_deg FLOAT,
            FOREIGN KEY (comet_id) REFERENCES comet_catalog(id),
            UNIQUE(comet_id, date_jd)
        )
    """)

    conn.commit()
    conn.close()

    yield db_path

    # Cleanup
    Path(db_path).unlink(missing_ok=True)
