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

        # Seestar mount path from config
        self.seestar_mount_path = Path(settings.seestar_mount_path)
        self.scan_extensions = settings.file_scan_extensions

    def list_available_files(self) -> List[Path]:
        """
        List all available files from Seestar mount.

        Returns:
            List of file paths from Seestar IMG directory.
            Returns empty list if mount not available.
        """
        if not self.seestar_mount_path.exists():
            self.logger.warning(f"Seestar mount path not found: {self.seestar_mount_path}")
            return []

        try:
            # Get all files recursively using configured extensions
            files = []
            for ext in self.scan_extensions:
                files.extend(self.seestar_mount_path.glob(f"**/*{ext}"))

            self.logger.info(f"Found {len(files)} files in {self.seestar_mount_path}")
            return files

        except (OSError, IOError, PermissionError) as e:
            self.logger.error(f"Error listing files from Seestar mount: {e}")
            return []
