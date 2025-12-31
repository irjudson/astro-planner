"""Tests for file transfer service."""

import pytest
from pathlib import Path
from datetime import datetime
from unittest.mock import MagicMock
import numpy as np
from astropy.io import fits
from app.services.file_transfer_service import FileTransferService
from app.services.file_scanner_service import FileScannerService
from app.models.capture_models import OutputFile


def test_file_transfer_service_init():
    """Test FileTransferService initialization."""
    service = FileTransferService()
    assert service is not None
    assert service.output_directory is not None


def _create_test_fits_file(file_path: Path, target_name: str):
    """Helper to create a minimal valid FITS file for testing."""
    # Create minimal FITS file with required metadata
    data = np.zeros((10, 10), dtype=np.uint16)
    hdu = fits.PrimaryHDU(data)
    hdu.header['OBJECT'] = target_name
    hdu.header['EXPTIME'] = 30.0
    hdu.header['FILTER'] = 'Luminance'
    hdu.header['CCD-TEMP'] = -10.5
    hdu.header['GAIN'] = 100
    hdu.header['DATE-OBS'] = '2025-12-30T20:30:00'
    hdu.writeto(file_path, overwrite=True)


@pytest.fixture
def mock_mount_path(tmp_path):
    """Create mock Seestar mount directory structure."""
    mount = tmp_path / "seestar_mount"
    mount.mkdir()

    # Create realistic Seestar directory structure
    # /seestar_mount/Seestar/IMG/
    img_dir = mount / "Seestar" / "IMG"
    img_dir.mkdir(parents=True)

    # Create proper FITS files with metadata
    _create_test_fits_file(img_dir / "M31_2025-12-30_001.fit", "M31")
    (img_dir / "M31_2025-12-30_001.jpg").write_text("fake jpg data")
    _create_test_fits_file(img_dir / "M42_2025-12-30_002.fit", "M42")

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


@pytest.fixture
def mock_db_session():
    """Create mock database session."""
    return MagicMock()


def test_transfer_and_scan_batch(mock_mount_path, tmp_path, mock_db_session):
    """Test transferring batch of files and scanning them."""
    service = FileTransferService()
    service.output_directory = tmp_path / "output"
    service.seestar_mount_path = mock_mount_path / "Seestar" / "IMG"

    # Transfer and scan all files
    results = service.transfer_and_scan_all(db=mock_db_session)

    # Should transfer 2 FITS files (JPG is skipped because it has no FITS metadata)
    assert results['transferred'] == 2
    assert results['scanned'] == 2
    assert results['errors'] == 0


def test_transfer_and_scan_with_errors(mock_mount_path, tmp_path, mock_db_session):
    """Test batch transfer handles errors gracefully."""
    service = FileTransferService()
    service.output_directory = tmp_path / "output"
    service.seestar_mount_path = mock_mount_path / "Seestar" / "IMG"

    # Add a file that will cause error (permission denied)
    bad_file = mock_mount_path / "Seestar" / "IMG" / "bad.fit"
    bad_file.write_text("data")
    bad_file.chmod(0o000)  # No permissions

    results = service.transfer_and_scan_all(db=mock_db_session)

    # Should handle error and continue with other files
    # The bad file will be skipped due to metadata extraction failure (returns None)
    # So we'll still have 2 transferred from the good files
    assert results['transferred'] == 2  # Original 2 good FITS files


def test_transfer_and_scan_idempotent(mock_mount_path, tmp_path, mock_db_session):
    """Test running transfer twice doesn't create duplicates."""
    service = FileTransferService()
    service.output_directory = tmp_path / "output"
    service.seestar_mount_path = mock_mount_path / "Seestar" / "IMG"

    # Run first transfer
    results1 = service.transfer_and_scan_all(db=mock_db_session)

    # Files are still on mount (not deleted by default)
    # Run transfer again - should skip existing files
    results2 = service.transfer_and_scan_all(db=mock_db_session)

    # First run should transfer 2 valid FITS files (JPG skipped due to no metadata)
    assert results1['transferred'] == 2
    assert results1['scanned'] == 2
    assert results1['errors'] == 0
    assert results1['skipped'] == 1  # JPG file skipped

    # Second run should skip FITS files that already exist at destination
    # JPG is still skipped due to metadata extraction failure
    assert results2['transferred'] == 0
    assert results2['skipped'] == 1  # JPG skipped again (already exists at destination)
    assert results2['errors'] == 0
    assert results2['scanned'] == 0
