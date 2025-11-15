# Pure Alembic Test Fixtures Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace Base.metadata schema operations with pure Alembic migrations in test fixtures to ensure tests use production migration path and avoid model import dependencies.

**Architecture:** Remove all `Base.metadata.drop_all()` and `Base.metadata.create_all()` calls from test fixtures. Use Alembic `downgrade("base")` and `upgrade("head")` exclusively for schema management. This ensures tests verify migrations work correctly and eliminates the need to track model imports for `Base.metadata`.

**Tech Stack:** SQLAlchemy, Alembic, pytest, PostgreSQL

**Root Cause:** `Base.metadata` has zero tables registered because catalog and processing models are never imported in a way that registers them with Base. This causes `Base.metadata.drop_all()` to be a no-op, leading to test database schema inconsistencies.

**Solution:** Use Alembic as single source of truth for all schema operations in tests.

---

## Task 1: Update Test Fixtures to Use Pure Alembic

**Files:**
- Modify: `backend/tests/conftest.py:28-45`

**Step 1: Write a test that verifies migrations create all expected tables**

Create: `backend/tests/test_migrations.py`

```python
"""Test that Alembic migrations work correctly."""

import pytest
from sqlalchemy import create_engine, text
from alembic.config import Config
from alembic import command

from app.core.config import get_settings


def test_migrations_create_all_tables():
    """Verify that running migrations creates all expected tables."""
    settings = get_settings()
    test_db_url = settings.test_database_url
    engine = create_engine(test_db_url)

    # Run downgrade to clean slate
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", test_db_url)
    command.downgrade(alembic_cfg, "base")

    # Verify no tables exist (except maybe alembic_version)
    with engine.connect() as conn:
        result = conn.execute(text(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public' "
            "AND tablename != 'alembic_version'"
        ))
        tables_before = [row[0] for row in result]
        assert tables_before == [], f"Expected no tables, found: {tables_before}"

    # Run upgrade to head
    command.upgrade(alembic_cfg, "head")

    # Verify all expected tables exist
    expected_tables = {
        'dso_catalog',
        'comet_catalog',
        'constellation_names',
        'processing_sessions',
        'processing_files',
        'processing_pipelines',
        'processing_jobs'
    }

    with engine.connect() as conn:
        result = conn.execute(text(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public' "
            "AND tablename != 'alembic_version'"
        ))
        tables_after = set(row[0] for row in result)

        assert tables_after == expected_tables, \
            f"Missing tables: {expected_tables - tables_after}, " \
            f"Extra tables: {tables_after - expected_tables}"

    # Clean up
    command.downgrade(alembic_cfg, "base")
```

**Step 2: Run test to verify current behavior**

```bash
cd backend
pytest tests/test_migrations.py::test_migrations_create_all_tables -v
```

Expected: Should PASS (migrations already work, we're just documenting it)

**Step 3: Update conftest.py to use pure Alembic**

Modify: `backend/tests/conftest.py`

Replace lines 28-45:

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

With:

```python
@pytest.fixture(scope="session", autouse=True)
def setup_test_db_schema():
    """Run Alembic migrations on test database before tests.

    Uses pure Alembic for schema management (no Base.metadata operations).
    This ensures tests run the same migration path as production.
    """
    from alembic.config import Config
    from alembic import command

    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)

    # Clean slate: downgrade to base (remove all tables)
    command.downgrade(alembic_cfg, "base")

    # Create all tables: upgrade to head
    command.upgrade(alembic_cfg, "head")

    yield

    # Cleanup: downgrade to base (remove all tables)
    command.downgrade(alembic_cfg, "base")
```

**Step 4: Run all tests to verify the fix works**

```bash
cd backend
pytest tests/test_comet_service.py -v
```

Expected: All comet service tests should now PASS (tables will exist)

```bash
pytest tests/test_services.py::TestCatalogService -v
```

Expected: Catalog service tests should continue to PASS

**Step 5: Commit the changes**

```bash
git add tests/conftest.py tests/test_migrations.py
git commit -m "fix: use pure Alembic for test schema management

- Replace Base.metadata.drop_all() with Alembic downgrade
- Replace manual migration with Alembic upgrade
- Add test to verify migrations create all tables
- Ensures tests use production migration path
- Eliminates dependency on model imports for schema ops

Fixes test failures where Base.metadata had zero registered tables"
```

---

## Task 2: Verify All Test Suites Pass

**Step 1: Run full test suite**

```bash
cd backend
pytest tests/ -v --tb=short
```

Expected: All tests should PASS, particularly:
- `test_comet_service.py` (4 tests that were failing)
- `test_services.py::TestCatalogService` (should continue passing)
- `test_migrations.py` (new test should pass)

**Step 2: Check test coverage for migration paths**

```bash
pytest tests/test_migrations.py -v --cov=alembic --cov-report=term-missing
```

Expected: Migration test covers downgrade and upgrade commands

**Step 3: Document the change in a test comment**

If all tests pass, add documentation to conftest.py explaining the approach:

```python
# NOTE: We use pure Alembic for all schema operations in tests.
# This has several advantages:
# - Single source of truth: Alembic migrations define schema
# - Production-like: Tests run the same code path as deployment
# - No import dependencies: Don't need to import models to register them
# - Migration testing: Verifies migrations actually work
#
# We do NOT use Base.metadata.drop_all() or Base.metadata.create_all()
# because Base.metadata only knows about models that are imported,
# which creates a maintenance burden and potential inconsistencies.
```

Add this comment above the `setup_test_db_schema` fixture.

**Step 4: Commit the documentation**

```bash
git add tests/conftest.py
git commit -m "docs: explain pure Alembic approach in test fixtures"
```

---

## Task 3: Clean Up Old SQLite Test Fixtures (Optional)

**Files:**
- Modify: `backend/tests/conftest.py:71-85`

**Context:** The `temp_db` fixture (lines 71-85) creates a SQLite database and is a leftover from the old SQLite-based testing approach. This is no longer needed since we're using PostgreSQL with Alembic.

**Step 1: Check if temp_db fixture is used anywhere**

```bash
cd backend
grep -r "temp_db" tests/ --include="*.py"
```

Expected: Should only find the definition in conftest.py, no usages

**Step 2: Remove the temp_db fixture if unused**

If grep shows no usages (except the definition), remove lines 71-85 from `backend/tests/conftest.py`:

```python
@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary SQLite database for testing."""
    # ... [delete entire fixture]
```

**Step 3: Run tests to verify nothing broke**

```bash
pytest tests/ -v
```

Expected: All tests still PASS (no test was using temp_db)

**Step 4: Commit the cleanup**

```bash
git add tests/conftest.py
git commit -m "refactor: remove unused SQLite temp_db fixture

Now using PostgreSQL with Alembic for all tests"
```

---

## Task 4: Fix Duplicate Migration Table Definitions

**Context:** The migration `79478a6f4f48_add_catalog_tables.py` incorrectly includes processing table definitions that were already created in `9a50fa4a1d87_add_processing_tables.py`. This happened because Alembic autogenerate saw ALL models when generating the migration.

**Files:**
- Modify: `backend/alembic/versions/79478a6f4f48_add_catalog_tables.py`

**Step 1: Verify the duplicate table issue**

```bash
cd backend
grep -A 5 "def upgrade" alembic/versions/79478a6f4f48_add_catalog_tables.py | head -20
```

Expected: Should show `op.create_table('comet_catalog'` AND `op.create_table('processing_pipelines'`

**Step 2: Create a new migration that ONLY has catalog tables**

Since the current migration was already run, we need to create a replacement:

```bash
cd backend
# Create a new empty migration
alembic revision -m "add_catalog_tables_only"
```

This creates a new file like `backend/alembic/versions/XXXXXX_add_catalog_tables_only.py`

**Step 3: Edit the new migration to only create catalog tables**

Open the new migration file and replace the `upgrade()` and `downgrade()` functions:

```python
def upgrade() -> None:
    """Create catalog tables only."""
    op.create_table('comet_catalog',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('designation', sa.String(length=50), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=True),
    sa.Column('discovery_date', sa.Date(), nullable=True),
    sa.Column('epoch_jd', sa.Float(), nullable=False),
    sa.Column('perihelion_distance_au', sa.Float(), nullable=False),
    sa.Column('eccentricity', sa.Float(), nullable=False),
    sa.Column('inclination_deg', sa.Float(), nullable=False),
    sa.Column('arg_perihelion_deg', sa.Float(), nullable=False),
    sa.Column('ascending_node_deg', sa.Float(), nullable=False),
    sa.Column('perihelion_time_jd', sa.Float(), nullable=False),
    sa.Column('absolute_magnitude', sa.Float(), nullable=False),
    sa.Column('magnitude_slope', sa.Float(), nullable=False),
    sa.Column('current_magnitude', sa.Float(), nullable=True),
    sa.Column('activity_status', sa.String(length=20), nullable=True),
    sa.Column('comet_type', sa.String(length=20), nullable=True),
    sa.Column('data_source', sa.String(length=100), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('designation')
    )
    op.create_index(op.f('ix_comet_catalog_id'), 'comet_catalog', ['id'], unique=False)

    op.create_table('constellation_names',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('abbreviation', sa.String(length=3), nullable=False),
    sa.Column('full_name', sa.String(length=50), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('abbreviation')
    )
    op.create_index(op.f('ix_constellation_names_id'), 'constellation_names', ['id'], unique=False)

    op.create_table('dso_catalog',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('catalog_name', sa.String(length=10), nullable=False),
    sa.Column('catalog_number', sa.Integer(), nullable=False),
    sa.Column('common_name', sa.String(length=100), nullable=True),
    sa.Column('ra_hours', sa.Float(), nullable=False),
    sa.Column('dec_degrees', sa.Float(), nullable=False),
    sa.Column('object_type', sa.String(length=50), nullable=False),
    sa.Column('magnitude', sa.Float(), nullable=True),
    sa.Column('surface_brightness', sa.Float(), nullable=True),
    sa.Column('size_major_arcmin', sa.Float(), nullable=True),
    sa.Column('size_minor_arcmin', sa.Float(), nullable=True),
    sa.Column('constellation', sa.String(length=3), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_dso_catalog_id'), 'dso_catalog', ['id'], unique=False)


def downgrade() -> None:
    """Drop catalog tables only."""
    op.drop_index(op.f('ix_dso_catalog_id'), table_name='dso_catalog')
    op.drop_table('dso_catalog')
    op.drop_index(op.f('ix_constellation_names_id'), table_name='constellation_names')
    op.drop_table('constellation_names')
    op.drop_index(op.f('ix_comet_catalog_id'), table_name='comet_catalog')
    op.drop_table('comet_catalog')
```

**Step 4: Test the corrected migration**

```bash
cd backend
# Test downgrade
alembic downgrade base
# Test upgrade
alembic upgrade head
# Verify tables exist
psql -h localhost -U pg -d test_astro_planner -c "\dt"
```

Expected: Should see only catalog and processing tables, no errors

**Step 5: Delete the old incorrect migration**

```bash
git rm alembic/versions/79478a6f4f48_add_catalog_tables.py
```

**Step 6: Commit the corrected migration**

```bash
git add alembic/versions/
git commit -m "fix: correct catalog migration to not duplicate processing tables

The previous migration included processing table definitions that were
already created in 9a50fa4a1d87. This migration only creates catalog
tables: comet_catalog, constellation_names, dso_catalog"
```

---

## Verification Checklist

After completing all tasks, verify:

- [ ] All tests pass: `pytest tests/ -v`
- [ ] Migration test passes: `pytest tests/test_migrations.py -v`
- [ ] Comet tests pass: `pytest tests/test_comet_service.py -v`
- [ ] Catalog tests pass: `pytest tests/test_services.py::TestCatalogService -v`
- [ ] Can run `alembic downgrade base` without errors
- [ ] Can run `alembic upgrade head` without errors
- [ ] No `Base.metadata.drop_all()` calls remain in conftest.py
- [ ] Migration creates exactly 7 tables (3 catalog + 4 processing)

---

## Success Criteria

1. All 136 tests pass
2. Test fixtures use only Alembic for schema operations
3. `Base.metadata` is never used for test schema management
4. Migrations can be run forward and backward without errors
5. No duplicate table definitions in migrations
