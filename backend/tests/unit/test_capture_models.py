"""Tests for capture history models."""

import pytest
from datetime import datetime
from app.models.capture_models import CaptureHistory


def test_capture_history_creation():
    """Test creating a CaptureHistory record."""
    capture = CaptureHistory(
        catalog_id="M31",
        total_exposure_seconds=7200,  # 2 hours
        total_frames=720,
        total_sessions=3,
        first_captured_at=datetime(2025, 12, 15, 20, 0),
        last_captured_at=datetime(2025, 12, 20, 22, 30),
        status="needs_more_data",
        suggested_status="needs_more_data",
        best_fwhm=2.3,
        best_star_count=2847
    )

    assert capture.catalog_id == "M31"
    assert capture.total_exposure_seconds == 7200
    assert capture.total_frames == 720
    assert capture.status == "needs_more_data"
