"""Pytest configuration and shared fixtures for PostgreSQL.

Database fixtures are lazy-loaded to avoid connection failures when running
non-integration tests (e.g., on macOS CI without database services).
"""

import sys
from pathlib import Path

import pytest

# Add app directory to Python path
app_dir = Path(__file__).parent.parent
sys.path.insert(0, str(app_dir))

# Lazy-loaded database components (only initialized when needed)
_test_engine = None
_TestSessionLocal = None


def _get_test_engine():
    """Lazily create the test database engine."""
    global _test_engine
    if _test_engine is None:
        from sqlalchemy import create_engine

        from app.core.config import get_settings

        settings = get_settings()
        TEST_DATABASE_URL = settings.test_database_url
        print(f"TEST_DATABASE_URL in conftest.py: {TEST_DATABASE_URL}")
        _test_engine = create_engine(TEST_DATABASE_URL)
    return _test_engine


def _get_test_session_local():
    """Lazily create the test session factory."""
    global _TestSessionLocal
    if _TestSessionLocal is None:
        from sqlalchemy.orm import sessionmaker

        _TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_get_test_engine())
    return _TestSessionLocal


@pytest.fixture(scope="session")
def setup_test_db_schema():
    """Run Alembic migrations on test database before tests.

    Uses pure Alembic for schema management (no Base.metadata operations).
    This ensures tests run the same migration path as production.

    CRITICAL: We tell Alembic to skip transaction wrappers (use_transaction=False)
    so DDL changes auto-commit and are immediately visible to all database
    connections. This is necessary because PostgreSQL's transactional DDL
    combined with pytest's transaction isolation would otherwise prevent
    tests from seeing the migrated schema.

    Note: When running in parallel with pytest-xdist, all workers share the
    same test database. We run migrations once and let all workers use the
    same schema. Cleanup is NOT done in teardown because it would interfere
    with other workers still running tests.

    This fixture is NOT autouse - it only runs for tests that need database access
    (via the client or override_get_db fixtures).
    """
    from alembic import command
    from alembic.config import Config

    from app.core.config import get_settings

    settings = get_settings()
    TEST_DATABASE_URL = settings.test_database_url

    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)

    # Tell env.py not to wrap migrations in begin_transaction()
    # This allows DDL to auto-commit in PostgreSQL
    alembic_cfg.attributes["use_transaction"] = False

    # Ensure database is at head revision (idempotent - won't re-run if already at head)
    command.upgrade(alembic_cfg, "head")

    # Load catalog data into test database (skips if already loaded)
    _load_test_catalog_data()

    yield

    # No cleanup - parallel workers share the database
    # Manual cleanup: docker-compose down -v or DROP DATABASE test_astro_planner


def _load_test_catalog_data():
    """Load sample catalog data into test database.

    Creates a minimal set of realistic DSO, constellation, and comet data
    that enables all tests to run without needing a production database.
    """
    from sqlalchemy.orm import Session

    from app.core.config import get_settings
    from app.models.catalog_models import CometCatalog, ConstellationName, DSOCatalog

    settings = get_settings()

    try:
        test_engine = _get_test_engine()

        with test_engine.connect() as conn:
            session = Session(bind=conn)

            # Check if data already loaded
            existing_count = session.query(ConstellationName).count()
            if existing_count > 0:
                print(f"Test catalog data already loaded ({existing_count} constellations)")
                return

            # Sample constellation data (covering objects we'll add)
            constellations = [
                {"abbreviation": "And", "full_name": "Andromeda"},
                {"abbreviation": "Ori", "full_name": "Orion"},
                {"abbreviation": "Sgr", "full_name": "Sagittarius"},
                {"abbreviation": "Cyg", "full_name": "Cygnus"},
                {"abbreviation": "Lyr", "full_name": "Lyra"},
                {"abbreviation": "Tau", "full_name": "Taurus"},
                {"abbreviation": "Gem", "full_name": "Gemini"},
                {"abbreviation": "Per", "full_name": "Perseus"},
                {"abbreviation": "Vir", "full_name": "Virgo"},
                {"abbreviation": "Com", "full_name": "Coma Berenices"},
            ]
            session.bulk_insert_mappings(ConstellationName, constellations)

            # Sample DSO data - 10 objects covering different types and catalogs
            dso_objects = [
                # Messier galaxies
                {
                    "catalog_name": "NGC",
                    "catalog_number": 224,
                    "common_name": "M031",
                    "object_type": "galaxy",
                    "ra_hours": 0.712,
                    "dec_degrees": 41.27,
                    "constellation": "And",
                    "magnitude": 3.4,
                    "caldwell_number": None,
                    "size_major_arcmin": 190.0,
                    "size_minor_arcmin": 60.0,
                },
                {
                    "catalog_name": "NGC",
                    "catalog_number": 4486,
                    "common_name": "M087",
                    "object_type": "galaxy",
                    "ra_hours": 12.514,
                    "dec_degrees": 12.39,
                    "constellation": "Vir",
                    "magnitude": 8.6,
                    "caldwell_number": None,
                    "size_major_arcmin": 8.3,
                    "size_minor_arcmin": 6.6,
                },
                # Messier nebulae
                {
                    "catalog_name": "NGC",
                    "catalog_number": 1976,
                    "common_name": "M042",
                    "object_type": "nebula",
                    "ra_hours": 5.588,
                    "dec_degrees": -5.39,
                    "constellation": "Ori",
                    "magnitude": 4.0,
                    "caldwell_number": None,
                    "size_major_arcmin": 85.0,
                    "size_minor_arcmin": 60.0,
                },
                {
                    "catalog_name": "NGC",
                    "catalog_number": 6720,
                    "common_name": "M057",
                    "object_type": "planetary_nebula",
                    "ra_hours": 18.893,
                    "dec_degrees": 33.03,
                    "constellation": "Lyr",
                    "magnitude": 8.8,
                    "caldwell_number": None,
                    "size_major_arcmin": 1.4,
                    "size_minor_arcmin": 1.0,
                },
                # Messier clusters
                {
                    "catalog_name": "NGC",
                    "catalog_number": 1912,
                    "common_name": "M038",
                    "object_type": "cluster",
                    "ra_hours": 5.478,
                    "dec_degrees": 35.85,
                    "constellation": "Gem",
                    "magnitude": 6.4,
                    "caldwell_number": None,
                    "size_major_arcmin": 21.0,
                    "size_minor_arcmin": 21.0,
                },
                {
                    "catalog_name": "NGC",
                    "catalog_number": 6913,
                    "common_name": "M029",
                    "object_type": "cluster",
                    "ra_hours": 20.399,
                    "dec_degrees": 38.52,
                    "constellation": "Cyg",
                    "magnitude": 6.6,
                    "caldwell_number": None,
                    "size_major_arcmin": 7.0,
                    "size_minor_arcmin": 7.0,
                },
                # IC object
                {
                    "catalog_name": "IC",
                    "catalog_number": 434,
                    "common_name": None,
                    "object_type": "nebula",
                    "ra_hours": 5.681,
                    "dec_degrees": -2.46,
                    "constellation": "Ori",
                    "magnitude": 7.3,
                    "caldwell_number": None,
                    "size_major_arcmin": 60.0,
                    "size_minor_arcmin": 10.0,
                },
                # Double Cluster (no Caldwell number to avoid duplicates with full catalog)
                {
                    "catalog_name": "NGC",
                    "catalog_number": 869,
                    "common_name": None,
                    "object_type": "cluster",
                    "ra_hours": 2.317,
                    "dec_degrees": 57.13,
                    "constellation": "Per",
                    "magnitude": 4.3,
                    "caldwell_number": None,
                    "size_major_arcmin": 30.0,
                    "size_minor_arcmin": 30.0,
                },
                {
                    "catalog_name": "NGC",
                    "catalog_number": 1952,
                    "common_name": "M001",
                    "object_type": "nebula",
                    "ra_hours": 5.575,
                    "dec_degrees": 22.01,
                    "constellation": "Tau",
                    "magnitude": 8.4,
                    "caldwell_number": None,
                    "size_major_arcmin": 6.0,
                    "size_minor_arcmin": 4.0,
                },
                # Additional faint object for magnitude filter tests
                {
                    "catalog_name": "NGC",
                    "catalog_number": 4889,
                    "common_name": None,
                    "object_type": "galaxy",
                    "ra_hours": 13.002,
                    "dec_degrees": 27.98,
                    "constellation": "Com",
                    "magnitude": 11.5,
                    "caldwell_number": None,
                    "size_major_arcmin": 2.9,
                    "size_minor_arcmin": 1.9,
                },
            ]
            session.bulk_insert_mappings(DSOCatalog, dso_objects)

            # Sample comet data - use unique designations that won't conflict with test fixtures
            comets = [
                {
                    "designation": "C/2021 TEST1",
                    "name": "Test Comet 1",
                    "epoch_jd": 2459000.5,
                    "perihelion_distance_au": 0.29,
                    "eccentricity": 0.999,
                    "inclination_deg": 128.9,
                    "arg_perihelion_deg": 37.3,
                    "ascending_node_deg": 61.0,
                    "perihelion_time_jd": 2459034.0,
                    "absolute_magnitude": 3.0,
                    "magnitude_slope": 4.0,
                    "current_magnitude": 7.0,
                    "comet_type": "long-period",
                    "activity_status": "active",
                    "data_source": "Test",
                    "notes": "Test comet fixture",
                },
                {
                    "designation": "C/2021 TEST2",
                    "name": "Test Comet 2",
                    "epoch_jd": 2459000.5,
                    "perihelion_distance_au": 1.243,
                    "eccentricity": 0.641,
                    "inclination_deg": 7.04,
                    "arg_perihelion_deg": 12.78,
                    "ascending_node_deg": 50.15,
                    "perihelion_time_jd": 2459131.0,
                    "absolute_magnitude": 11.3,
                    "magnitude_slope": 10.0,
                    "current_magnitude": 12.0,
                    "comet_type": "short-period",
                    "activity_status": "active",
                    "data_source": "Test",
                    "notes": "Test comet fixture",
                },
            ]
            session.bulk_insert_mappings(CometCatalog, comets)

            session.commit()
            print(
                f"Loaded {len(constellations)} constellations, {len(dso_objects)} DSOs, and {len(comets)} comets into test database"
            )

    except Exception as e:
        print(f"Warning: Could not load test catalog data: {e}")
        import traceback

        traceback.print_exc()


@pytest.fixture(scope="function")
def override_get_db(setup_test_db_schema):
    """Override the get_db dependency to use a transactional test session.

    Depends on setup_test_db_schema to ensure migrations are run first.
    """
    from app.database import get_db
    from app.main import app

    test_engine = _get_test_engine()
    TestSessionLocal = _get_test_session_local()

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

    from app.main import app

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
        raise FileNotFoundError(
            f"Catalog database not found at {source_db}. Run scripts/import_catalog.py and scripts/add_comet_tables.py first."
        )


@pytest.fixture
def sample_fits_file(tmp_path):
    """Create a dummy FITS file for testing uploads."""
    import numpy as np
    from astropy.io import fits

    # Create a simple FITS header
    hdr = fits.Header()
    hdr["EXPTIME"] = 30.0
    hdr["FILTER"] = "R"
    hdr["OBJECT"] = "M31"

    # Create dummy data
    data = np.random.rand(100, 100).astype(np.float32)

    # Create a new FITS HDU
    hdu = fits.PrimaryHDU(data=data, header=hdr)
    hdul = fits.HDUList([hdu])

    # Save to a temporary file
    file_path = tmp_path / "test_image.fits"
    hdul.writeto(file_path, overwrite=True)
    return file_path
