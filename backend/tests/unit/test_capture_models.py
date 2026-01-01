"""Tests for capture history models."""

import pytest
from datetime import datetime
from app.models.capture_models import CaptureHistory, OutputFile


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
        best_star_count=2847,
    )

    assert capture.catalog_id == "M31"
    assert capture.total_exposure_seconds == 7200
    assert capture.total_frames == 720
    assert capture.status == "needs_more_data"


def test_output_file_creation():
    """Test creating an OutputFile record."""
    output_file = OutputFile(
        file_path="/mnt/astronomy/M31/2025-12-29/M31_stacked.fit",
        file_type="stacked_fits",
        file_size_bytes=458392847,
        catalog_id="M31",
        catalog_id_confidence=0.95,
        execution_id=None,
        execution_target_id=None,
        exposure_seconds=10,
        filter_name="LP",
        temperature_celsius=-10.0,
        gain=80,
        fwhm=2.3,
        star_count=2847,
        observation_date=datetime(2025, 12, 29, 21, 45),
    )

    assert output_file.file_path == "/mnt/astronomy/M31/2025-12-29/M31_stacked.fit"
    assert output_file.file_type == "stacked_fits"
    assert output_file.catalog_id == "M31"
    assert output_file.catalog_id_confidence == 0.95


def test_capture_history_output_file_relationship():
    """Test relationship between CaptureHistory and OutputFile."""
    # This will be tested after relationships are set up
    pass  # Placeholder for now
