"""Tests for file scanner service."""

from unittest.mock import Mock
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
