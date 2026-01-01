"""Tests for configuration settings."""

import pytest

from app.core.config import Settings


def test_capture_settings_defaults():
    """Test capture-related configuration defaults."""
    settings = Settings()

    assert settings.output_directory == "/mnt/synology/shared/Astronomy"
    assert settings.auto_transfer_files is True
    assert settings.auto_delete_after_transfer is True
    assert settings.capture_complete_hours == 3.0
    assert settings.capture_needs_more_hours == 1.0
    assert settings.file_scan_extensions == [".fit", ".fits", ".jpg", ".png", ".tiff", ".avi"]
