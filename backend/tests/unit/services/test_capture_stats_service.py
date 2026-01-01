"""Tests for capture statistics service."""

from datetime import datetime

import pytest

from app.models.capture_models import CaptureHistory, OutputFile
from app.services.capture_stats_service import CaptureStatsService

# Mark all tests in this module as integration tests (require database)
pytestmark = pytest.mark.integration


@pytest.fixture
def sample_output_files(override_get_db):
    """Create sample output files for testing."""
    files = [
        OutputFile(
            file_path="/output/M31/2025-12-30/file1.fit",
            file_type="stacked_fits",
            file_size_bytes=1000000,
            catalog_id="M31",
            catalog_id_confidence=1.0,
            exposure_seconds=10,
            observation_date=datetime(2025, 12, 30, 21, 0),
        ),
        OutputFile(
            file_path="/output/M31/2025-12-30/file2.fit",
            file_type="stacked_fits",
            file_size_bytes=1000000,
            catalog_id="M31",
            catalog_id_confidence=1.0,
            exposure_seconds=10,
            observation_date=datetime(2025, 12, 30, 22, 0),
        ),
        OutputFile(
            file_path="/output/M31/2025-12-31/file3.fit",
            file_type="stacked_fits",
            file_size_bytes=1000000,
            catalog_id="M31",
            catalog_id_confidence=1.0,
            exposure_seconds=10,
            observation_date=datetime(2025, 12, 31, 20, 0),
        ),
    ]

    for f in files:
        override_get_db.add(f)
    override_get_db.commit()

    return files


def test_aggregate_capture_history(override_get_db, sample_output_files):
    """Test aggregating output files into capture history."""
    service = CaptureStatsService(override_get_db)

    service.update_capture_history("M31")

    capture = override_get_db.query(CaptureHistory).filter(CaptureHistory.catalog_id == "M31").first()

    assert capture is not None
    assert capture.total_frames == 3
    assert capture.total_exposure_seconds == 30
    assert capture.total_sessions == 2  # Two different dates
    assert capture.first_captured_at == datetime(2025, 12, 30, 21, 0)
    assert capture.last_captured_at == datetime(2025, 12, 31, 20, 0)


def test_update_suggested_status(override_get_db, sample_output_files):
    """Test suggested status calculation."""
    service = CaptureStatsService(override_get_db)

    service.update_capture_history("M31")

    capture = override_get_db.query(CaptureHistory).filter(CaptureHistory.catalog_id == "M31").first()

    # With 30 seconds total (0.008 hours), should not suggest any status
    # (below the 1.0 hour threshold for "needs_more_data")
    assert capture.suggested_status is None
