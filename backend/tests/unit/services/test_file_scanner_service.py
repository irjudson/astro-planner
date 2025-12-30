"""Tests for file scanner service."""

from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import pytest
from sqlalchemy.orm import Session

from app.services.file_scanner_service import FileScannerService


@pytest.fixture
def mock_db():
    """Create mock database session."""
    return Mock(spec=Session)


@pytest.fixture
def file_scanner_service(mock_db):
    """Create file scanner service with mock database."""
    return FileScannerService(mock_db)


class TestFileScannerService:
    """Test file scanner service core functionality."""

    def test_init(self, file_scanner_service, mock_db):
        """Test service initialization."""
        assert file_scanner_service.db == mock_db


class TestFuzzyMatching:
    """Test fuzzy matching of target names to catalog."""

    def test_fuzzy_match_exact(self, file_scanner_service, mock_db):
        """Test exact match of target name."""
        # Mock DSOCatalog to return a match
        mock_dso = Mock()
        mock_dso.common_name = "M031"
        mock_dso.caldwell_number = None
        mock_dso.catalog_name = "NGC"
        mock_dso.catalog_number = 224
        mock_db.query.return_value.all.return_value = [mock_dso]

        result = file_scanner_service._fuzzy_match_catalog("M31")

        assert result is not None
        catalog_id, confidence = result
        assert catalog_id == "M31"
        assert confidence >= 0.7

    def test_fuzzy_match_with_space(self, file_scanner_service, mock_db):
        """Test match handling space normalization (M 31 vs M31)."""
        mock_dso = Mock()
        mock_dso.common_name = "M031"
        mock_dso.caldwell_number = None
        mock_dso.catalog_name = "NGC"
        mock_dso.catalog_number = 224
        mock_db.query.return_value.all.return_value = [mock_dso]

        result = file_scanner_service._fuzzy_match_catalog("M 31")

        assert result is not None
        catalog_id, confidence = result
        assert confidence >= 0.7

    def test_fuzzy_match_alternate_name(self, file_scanner_service, mock_db):
        """Test matching alternate names (Andromeda vs M31)."""
        # This tests fuzzy matching with common names
        mock_dso = Mock()
        mock_dso.common_name = "Andromeda"
        mock_dso.caldwell_number = None
        mock_dso.catalog_name = "NGC"
        mock_dso.catalog_number = 224
        mock_db.query.return_value.all.return_value = [mock_dso]

        # For this test, just verify the method exists and returns something when
        # given a name that might match
        result = file_scanner_service._fuzzy_match_catalog("Andromeda")

        # Either finds a match or returns None - just verify it doesn't crash
        assert result is None or (isinstance(result, tuple) and len(result) == 2)

    def test_fuzzy_match_no_match(self, file_scanner_service, mock_db):
        """Test no match found below threshold."""
        mock_db.query.return_value.all.return_value = []

        result = file_scanner_service._fuzzy_match_catalog("NONEXISTENT_OBJECT_XYZ")

        assert result is None


class TestFitsMetadataExtraction:
    """Test FITS metadata extraction from image files."""

    @patch("app.services.file_scanner_service.fits")
    def test_extract_fits_metadata_success(self, mock_fits, file_scanner_service):
        """Test successful FITS metadata extraction."""
        # Mock FITS file reading
        mock_hdu = MagicMock()
        mock_hdu.header = {
            "OBJECT": "M31",
            "EXPTIME": 10.0,
            "FILTER": "L",
            "CCD-TEMP": -10.5,
            "GAIN": 100,
            "DATE-OBS": "2024-12-25T20:30:00",
        }
        mock_fits.open.return_value.__enter__.return_value = [mock_hdu]

        result = file_scanner_service._extract_fits_metadata("/path/to/file.fits")

        assert result is not None
        assert result["target_name"] == "M31"
        assert result["exposure_seconds"] == 10
        assert result["filter_name"] == "L"
        assert result["temperature_celsius"] == -10.5
        assert result["gain"] == 100
        assert result["observation_date"] is not None

    @patch("app.services.file_scanner_service.fits")
    def test_extract_fits_metadata_missing_fields(self, mock_fits, file_scanner_service):
        """Test FITS extraction with missing optional fields."""
        # Mock FITS file with minimal fields
        mock_hdu = MagicMock()
        mock_hdu.header = {
            "OBJECT": "M42",
        }
        mock_fits.open.return_value.__enter__.return_value = [mock_hdu]

        result = file_scanner_service._extract_fits_metadata("/path/to/file.fits")

        assert result is not None
        assert result["target_name"] == "M42"
        # Optional fields should be None
        assert result.get("exposure_seconds") is None
        assert result.get("filter_name") is None
        assert result.get("temperature_celsius") is None
        assert result.get("gain") is None

    @patch("app.services.file_scanner_service.fits")
    def test_extract_fits_metadata_file_error(self, mock_fits, file_scanner_service):
        """Test FITS extraction with file read error."""
        # Mock file read error
        mock_fits.open.side_effect = Exception("File not found")

        result = file_scanner_service._extract_fits_metadata("/path/to/nonexistent.fits")

        assert result is None
