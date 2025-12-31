"""Tests for file transfer service."""

import pytest
from pathlib import Path
from app.services.file_transfer_service import FileTransferService


def test_file_transfer_service_init():
    """Test FileTransferService initialization."""
    service = FileTransferService()
    assert service is not None
    assert service.output_directory is not None
