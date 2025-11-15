"""Test that Alembic migrations work correctly."""

import pytest
from sqlalchemy import create_engine, text

from app.core.config import get_settings


def test_fixture_creates_all_tables():
    """Verify that the setup_test_db_schema fixture creates all expected tables.

    This test relies on the autouse setup_test_db_schema fixture to run migrations.
    We just verify that all tables exist after the fixture runs.
    """
    settings = get_settings()
    test_db_url = settings.test_database_url
    engine = create_engine(test_db_url)

    # Verify all expected tables exist (created by setup_test_db_schema fixture)
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
        tables_found = set(row[0] for row in result)

        assert tables_found == expected_tables, \
            f"Missing tables: {expected_tables - tables_found}, " \
            f"Extra tables: {tables_found - expected_tables}"
