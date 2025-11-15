"""Pytest configuration and shared fixtures for PostgreSQL."""

import pytest
import sys
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# Add app directory to Python path
app_dir = Path(__file__).parent.parent
sys.path.insert(0, str(app_dir))

from app.main import app
from app.database import get_db, Base # Import Base from app.database
from app.core.config import get_settings

settings = get_settings()

# Use a separate test database URL
TEST_DATABASE_URL = settings.test_database_url

test_engine = create_engine(TEST_DATABASE_URL)
print(f"TEST_DATABASE_URL in conftest.py: {TEST_DATABASE_URL}")
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

@pytest.fixture(scope="session", autouse=True)
def setup_test_db_schema():
    """Run Alembic migrations on test database before tests.

    Uses pure Alembic for schema management (no Base.metadata operations).
    This ensures tests run the same migration path as production.

    CRITICAL: We tell Alembic to skip transaction wrappers (use_transaction=False)
    so DDL changes auto-commit and are immediately visible to all database
    connections. This is necessary because PostgreSQL's transactional DDL
    combined with pytest's transaction isolation would otherwise prevent
    tests from seeing the migrated schema.
    """
    from alembic.config import Config
    from alembic import command

    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)

    # Tell env.py not to wrap migrations in begin_transaction()
    # This allows DDL to auto-commit in PostgreSQL
    alembic_cfg.attributes['use_transaction'] = False

    # Clean slate: downgrade to base (remove all tables)
    command.downgrade(alembic_cfg, "base")

    # Create all tables: upgrade to head
    command.upgrade(alembic_cfg, "head")

    yield

    # Cleanup: downgrade to base (remove all tables)
    command.downgrade(alembic_cfg, "base")

@pytest.fixture(scope="function")
def override_get_db():
    """Override the get_db dependency to use a transactional test session."""
    connection = test_engine.connect()
    transaction = connection.begin()
    db = TestSessionLocal(bind=connection)

    app.dependency_overrides[get_db] = lambda: db

    try:
        yield db
    finally:
        transaction.rollback()
        connection.close()
        app.dependency_overrides.clear()

# Fixture to provide a client that uses the overridden database dependency
@pytest.fixture(scope="function")
def client(override_get_db):
    """Test client that uses the overridden database dependency."""
    from fastapi.testclient import TestClient
    with TestClient(app) as c:
        yield c

@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary SQLite database for testing."""
    import shutil
    # Copy the main catalog database to a temp location
    # This ensures all tables (DSO, comet, etc.) are available with correct schema
    source_db = Path(__file__).parent.parent / "data" / "catalogs.db"
    temp_db_path = tmp_path / "test_catalogs.db"
    if source_db.exists():
        shutil.copy(source_db, temp_db_path)
        return str(temp_db_path)
    else:
        # If source doesn't exist, tests will fail - this is intentional
        # as it indicates the catalog database hasn't been set up
        raise FileNotFoundError(f"Catalog database not found at {source_db}. Run scripts/import_catalog.py and scripts/add_comet_tables.py first.")

@pytest.fixture
def sample_fits_file(tmp_path):
    """Create a dummy FITS file for testing uploads."""
    from astropy.io import fits
    import numpy as np

    # Create a simple FITS header
    hdr = fits.Header()
    hdr['EXPTIME'] = 30.0
    hdr['FILTER'] = 'R'
    hdr['OBJECT'] = 'M31'

    # Create dummy data
    data = np.random.rand(100, 100).astype(np.float32)

    # Create a new FITS HDU
    hdu = fits.PrimaryHDU(data=data, header=hdr)
    hdul = fits.HDUList([hdu])

    # Save to a temporary file
    file_path = tmp_path / "test_image.fits"
    hdul.writeto(file_path, overwrite=True)
    return file_path