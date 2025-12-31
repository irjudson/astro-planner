"""File transfer service for downloading Seestar S50 captures."""

import logging
import shutil
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.services.file_scanner_service import FileScannerService


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

        # Scanner will be initialized when needed with a DB session
        self.scanner = None

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

    def _get_destination_path(
        self,
        source_file: Path,
        target_name: str,
        observation_date: datetime
    ) -> Path:
        """
        Generate organized destination path.

        Organization: {output_directory}/{target_name}/{YYYY-MM-DD}/{filename}

        Args:
            source_file: Original file path
            target_name: Catalog target name (e.g., "M31")
            observation_date: Observation datetime

        Returns:
            Organized destination path

        Raises:
            ValueError: If target_name contains path traversal sequences
        """
        # Validate target_name for security
        if ".." in target_name or "/" in target_name or "\\" in target_name:
            raise ValueError(f"Invalid target name (path traversal detected): {target_name}")

        date_str = observation_date.strftime("%Y-%m-%d")
        dest_dir = self.output_directory / target_name / date_str
        return dest_dir / source_file.name

    def transfer_file(
        self,
        source_file: Path,
        target_name: str,
        observation_date: datetime,
        delete_source: bool = False
    ) -> Path:
        """
        Transfer file to organized destination.

        Args:
            source_file: Source file path
            target_name: Catalog target name
            observation_date: Observation datetime
            delete_source: Delete source after successful transfer

        Returns:
            Destination file path
        """
        dest_path = self._get_destination_path(source_file, target_name, observation_date)

        # Skip if file already exists
        if dest_path.exists():
            self.logger.debug(f"File already exists, skipping: {dest_path}")
            return dest_path

        # Create destination directory
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            # Copy file
            shutil.copy2(source_file, dest_path)
            self.logger.info(f"Transferred: {source_file.name} -> {dest_path}")

            # Delete source if requested
            if delete_source:
                source_file.unlink()
                self.logger.debug(f"Deleted source file: {source_file}")

            return dest_path

        except Exception as e:
            self.logger.error(f"Error transferring file {source_file}: {e}")
            raise

    def transfer_and_scan_all(self, db: Session) -> Dict[str, Any]:
        """
        Transfer all files from Seestar and scan them.

        This is the main orchestration method that:
        1. Lists available files from Seestar
        2. Extracts metadata to determine target/date
        3. Transfers files to organized structure
        4. Scans transferred files with FileScannerService

        Args:
            db: Database session for creating OutputFile records

        Returns:
            Dict with counts: transferred, scanned, errors
        """
        results = {
            'transferred': 0,
            'scanned': 0,
            'errors': 0,
            'skipped': 0
        }

        # Initialize scanner with DB session
        self.scanner = FileScannerService(db)

        # Get all available files
        available_files = self.list_available_files()
        if not available_files:
            self.logger.info("No files available for transfer")
            return results

        self.logger.info(f"Found {len(available_files)} files to process")

        # Transfer and scan each file
        for source_file in available_files:
            try:
                # Extract metadata to get target name and date
                metadata = self.scanner._extract_fits_metadata(str(source_file))

                if not metadata or not metadata.get('target_name'):
                    self.logger.warning(f"Could not extract metadata from {source_file.name}, skipping")
                    results['skipped'] += 1
                    continue

                target_name = metadata['target_name']
                observation_date = metadata.get('observation_date') or datetime.now()

                # Transfer file
                dest_path = self.transfer_file(
                    source_file,
                    target_name,
                    observation_date,
                    delete_source=self.auto_delete
                )

                results['transferred'] += 1

                # Scan the single transferred file's directory (parent)
                # This ensures we only scan newly transferred files, not entire output directory
                scan_count = self.scanner.scan_files(str(dest_path.parent), db)
                if scan_count > 0:
                    results['scanned'] += 1

            except Exception as e:
                self.logger.error(f"Error processing {source_file}: {e}")
                results['errors'] += 1

        self.logger.info(f"Transfer complete: {results}")
        return results
