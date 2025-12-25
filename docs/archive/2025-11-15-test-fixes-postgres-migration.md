# Test Fixes via PostgreSQL Migration

**Date:** 2025-11-15
**Status:** Approved for Implementation
**Goal:** Fix 23 failing tests by migrating catalog data from SQLite to PostgreSQL

## Problem Statement

The test suite has 23 failures split into two categories:

1. **Comet service tests (4 failures)** - Missing `comet_catalog` table because `CometService` uses SQLite while tests expect PostgreSQL
2. **Processing integration tests (19 failures)** - Test database not properly initialized with migrations

## Current Architecture

- **Processing tables**: Use PostgreSQL via SQLAlchemy/Alembic
- **Catalog tables** (DSO, comets): Use SQLite via raw SQL
- **Test setup**: Incomplete - doesn't run migrations on test database

## Solution Approach

Migrate all catalog data to PostgreSQL and refactor services to use SQLAlchemy ORM consistently.

## Database Schema Migration

### Create New Alembic Migration

**`dso_catalog` table:**
- `id` INTEGER PRIMARY KEY
- `catalog` VARCHAR (NGC/IC)
- `catalog_id` INTEGER (object number)
- `name` VARCHAR
- `common_name` VARCHAR
- `object_type` VARCHAR (galaxy, nebula, cluster, etc.)
- `ra_hours` FLOAT (right ascension)
- `dec_degrees` FLOAT (declination)
- `constellation` VARCHAR
- `magnitude` FLOAT
- `surface_brightness` FLOAT
- `size_arcmin` FLOAT (apparent size)
- `distance_mly` FLOAT (distance in millions of light years)
- `description` TEXT

**`comet_catalog` table:**
- `id` INTEGER PRIMARY KEY
- `designation` VARCHAR
- `name` VARCHAR
- `discovery_date` DATE
- `epoch_jd` FLOAT (Julian date of epoch)
- `perihelion_distance_au` FLOAT
- `eccentricity` FLOAT
- `inclination_deg` FLOAT
- `arg_perihelion_deg` FLOAT (argument of perihelion)
- `ascending_node_deg` FLOAT
- `perihelion_time_jd` FLOAT
- `absolute_magnitude` FLOAT
- `magnitude_slope` FLOAT
- `current_magnitude` FLOAT
- `activity_status` VARCHAR
- `comet_type` VARCHAR
- `data_source` VARCHAR
- `notes` TEXT

## Service Layer Refactoring

### Convert from SQLite to SQLAlchemy

**Changes to `CometService`:**
- Remove `sqlite3` imports and `_get_connection()` method
- Add SQLAlchemy session dependency injection
- Replace raw SQL with ORM queries
- Example: `cursor.execute("SELECT * FROM comet_catalog")` → `session.query(CometCatalog).all()`

**Changes to `CatalogService`:**
- Same pattern - replace SQLite with SQLAlchemy
- Use ORM models for DSO catalog queries
- Filter, sort, and join via SQLAlchemy query API

### Create SQLAlchemy Models

Add `app/models/catalog_models.py`:
- `DSOCatalog` model (maps to `dso_catalog` table)
- `CometCatalog` model (maps to `comet_catalog` table)
- Use declarative base from `app/database.py`

### Dependency Injection

Services receive database session via FastAPI's dependency injection:
```python
def get_catalog_service(db: Session = Depends(get_db)):
    return CatalogService(db)
```

## Test Infrastructure Updates

### Update `conftest.py`

**Add migration runner:**
```python
@pytest.fixture(scope="session", autouse=True)
def setup_test_db_schema():
    """Run Alembic migrations on test database before tests."""
    from alembic.config import Config
    from alembic import command

    # Drop all tables (clean slate)
    Base.metadata.drop_all(bind=test_engine)

    # Run migrations
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)
    command.upgrade(alembic_cfg, "head")

    yield

    # Cleanup
    Base.metadata.drop_all(bind=test_engine)
```

**Remove obsolete fixtures:**
- Remove `temp_db` fixture (no longer needed)
- Existing `override_get_db` handles transactional rollback

**Add test data seeding:**
- Fixture to insert sample catalog data for tests
- Few DSO objects and comets for query testing

## Data Migration

### Create Import Script

`scripts/migrate_catalog_to_postgres.py`:
1. Connect to SQLite `catalogs.db`
2. Connect to PostgreSQL
3. Read all DSO and comet records
4. Bulk insert via SQLAlchemy
5. Verify record counts match

**Run once during deployment:**
- After Alembic migrations create tables
- Before removing SQLite dependency
- Idempotent (checks if data exists)

## Implementation Plan

**Order of execution:**

1. Create SQLAlchemy models (`app/models/catalog_models.py`)
2. Create Alembic migration for catalog tables
3. Run migration on dev database
4. Create and run data import script
5. Refactor `CatalogService` to use SQLAlchemy
6. Refactor `CometService` to use SQLAlchemy
7. Update test fixtures to run migrations
8. Run tests - verify all pass
9. Clean up old SQLite code

**Estimated effort:** 2-3 hours

## Success Criteria

- All 23 failing tests pass
- Catalog queries work identically to SQLite version
- Test database properly initialized with migrations
- Single PostgreSQL database for all data
- No SQLite dependencies remain

## Rollback Plan

If issues arise:
- Git revert to previous commit
- Keep SQLite as fallback until PostgreSQL stable
- Migrations can be rolled back with `alembic downgrade`

## Future Considerations

- Add database indexes for common queries (constellation, magnitude, object_type)
- Consider full-text search for object names
- Add caching layer for frequently accessed catalog data
- Evaluate partitioning for large comet ephemeris calculations
