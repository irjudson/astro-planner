"""Tests for file transfer service."""

import pytest
from pathlib import Path
from datetime import datetime
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


def test_organize_file_path():
    """Test generating organized destination path for file."""
    service = FileTransferService()
    service.output_directory = Path("/output")

    source_file = Path("/seestar/M31_2025-12-30_001.fit")

    dest_path = service._get_destination_path(
        source_file,
        target_name="M31",
        observation_date=datetime(2025, 12, 30, 21, 45)
    )

    # Should organize as: /output/M31/2025-12-30/M31_2025-12-30_001.fit
    assert "M31" in str(dest_path)
    assert "2025-12-30" in str(dest_path)
    assert dest_path.name == "M31_2025-12-30_001.fit"


def test_transfer_file(mock_mount_path, tmp_path):
    """Test transferring single file with organization."""
    service = FileTransferService()
    service.output_directory = tmp_path / "output"
    service.seestar_mount_path = mock_mount_path / "Seestar" / "IMG"

    source = mock_mount_path / "Seestar" / "IMG" / "M31_2025-12-30_001.fit"

    transferred_path = service.transfer_file(
        source,
        target_name="M31",
        observation_date=datetime(2025, 12, 30, 21, 45)
    )

    assert transferred_path.exists()
    assert "M31" in str(transferred_path)
    assert "2025-12-30" in str(transferred_path)


def test_transfer_file_already_exists(mock_mount_path, tmp_path):
    """Test skipping file that already exists at destination."""
    service = FileTransferService()
    service.output_directory = tmp_path / "output"

    # Create existing file
    dest_dir = service.output_directory / "M31" / "2025-12-30"
    dest_dir.mkdir(parents=True)
    existing = dest_dir / "M31_2025-12-30_001.fit"
    existing.write_text("existing data")

    source = mock_mount_path / "Seestar" / "IMG" / "M31_2025-12-30_001.fit"

    # Should skip and return existing path
    result = service.transfer_file(
        source,
        target_name="M31",
        observation_date=datetime(2025, 12, 30, 21, 45)
    )

    assert result == existing
    assert existing.read_text() == "existing data"  # Not overwritten


def test_transfer_file_path_traversal_protection(mock_mount_path, tmp_path):
    """Test protection against path traversal attacks in target_name."""
    service = FileTransferService()
    service.output_directory = tmp_path / "output"

    source = mock_mount_path / "Seestar" / "IMG" / "M31_2025-12-30_001.fit"

    # Attempt path traversal attack
    with pytest.raises(ValueError, match="Invalid target name"):
        service.transfer_file(
            source,
            target_name="../../../tmp/evil",
            observation_date=datetime(2025, 12, 30, 21, 45)
        )


def test_transfer_file_with_delete_source(mock_mount_path, tmp_path):
    """Test file transfer with source deletion."""
    service = FileTransferService()
    service.output_directory = tmp_path / "output"

    source = mock_mount_path / "Seestar" / "IMG" / "M31_2025-12-30_001.fit"

    # Verify source exists before transfer
    assert source.exists()

    transferred_path = service.transfer_file(
        source,
        target_name="M31",
        observation_date=datetime(2025, 12, 30, 21, 45),
        delete_source=True
    )

    # Verify transfer succeeded
    assert transferred_path.exists()

    # Verify source was deleted
    assert not source.exists()
