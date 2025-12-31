"""File transfer service for downloading Seestar S50 captures."""

import logging
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from app.core.config import get_settings


class FileTransferService:
    """Downloads and organizes capture files from Seestar S50."""

    def __init__(self):
        """Initialize file transfer service."""
        self.logger = logging.getLogger(__name__)
        settings = get_settings()
        self.output_directory = Path(settings.output_directory)
        self.auto_transfer = settings.auto_transfer_files
        self.auto_delete = settings.auto_delete_after_transfer
