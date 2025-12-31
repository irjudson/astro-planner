"""Tests for file transfer service."""

import pytest
from pathlib import Path
from app.services.file_transfer_service import FileTransferService


def test_file_transfer_service_init():
    """Test FileTransferService initialization."""
    service = FileTransferService()
    assert service is not None
    assert service.output_directory is not None


@pytest.fixture
def mock_mount_path(tmp_path):
    """Create mock Seestar mount directory structure."""
    mount = tmp_path / "seestar_mount"
    mount.mkdir()

    # Create realistic Seestar directory structure
    # /seestar_mount/Seestar/IMG/
    img_dir = mount / "Seestar" / "IMG"
    img_dir.mkdir(parents=True)

    # Create some test files
    (img_dir / "M31_2025-12-30_001.fit").write_text("fake fits data")
    (img_dir / "M31_2025-12-30_001.jpg").write_text("fake jpg data")
    (img_dir / "M42_2025-12-30_002.fit").write_text("fake fits data")

    return mount


def test_list_files_from_mount(mock_mount_path):
    """Test listing files from mounted Seestar directory."""
    service = FileTransferService()

    # Override mount path for testing
    service.seestar_mount_path = mock_mount_path / "Seestar" / "IMG"

    files = service.list_available_files()

    assert len(files) == 3
    assert any("M31_2025-12-30_001.fit" in str(f) for f in files)
    assert any("M42_2025-12-30_002.fit" in str(f) for f in files)


def test_list_files_mount_not_available():
    """Test graceful handling when mount is not available."""
    service = FileTransferService()
    service.seestar_mount_path = Path("/nonexistent/path")

    files = service.list_available_files()

    assert files == []
