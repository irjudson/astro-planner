"""File scanner service for discovering and processing image files."""

import os
from typing import Optional, Tuple, Dict, Any
from datetime import datetime
from thefuzz import fuzz
from sqlalchemy.orm import Session
from astropy.io import fits

from app.core.config import get_settings
from app.models.capture_models import OutputFile
from app.models.catalog_models import DSOCatalog


class FileScannerService:
    """Service for scanning directories and processing image files."""

    def __init__(self, db: Session):
        """Initialize file scanner service with database session."""
        self.db = db

    def _fuzzy_match_catalog(self, target_name: str) -> Optional[Tuple[str, float]]:
        """
        Fuzzy match a target name to catalog.

        Handles variations like "M 31" vs "M31" vs "Andromeda".

        Args:
            target_name: Target name to match (e.g., "M31", "M 31", "Andromeda")

        Returns:
            Tuple of (catalog_id, confidence) or None if no match above threshold
        """
        if not target_name or not target_name.strip():
            return None

        # Normalize input name - remove spaces for better matching
        normalized_input = target_name.strip().upper().replace(" ", "")
        threshold = 70  # 70% confidence minimum

        # Get all DSO catalog entries
        all_dsos = self.db.query(DSOCatalog).all()

        best_match = None
        best_score = 0

        for dso in all_dsos:
            # Try matching against common_name
            if dso.common_name:
                # Normalize database value - remove spaces
                db_name = dso.common_name.strip().upper().replace(" ", "")
                # Use token_set_ratio for better matching
                score = fuzz.token_set_ratio(normalized_input, db_name)
                if score > best_score:
                    best_score = score
                    # Generate catalog ID
                    if dso.common_name.startswith("M") and len(dso.common_name) > 1 and dso.common_name[1:].isdigit():
                        # Messier: M031 -> M31
                        catalog_id = f"M{int(dso.common_name[1:])}"
                    elif dso.caldwell_number:
                        catalog_id = f"C{dso.caldwell_number}"
                    else:
                        catalog_id = f"{dso.catalog_name}{dso.catalog_number}"
                    best_match = catalog_id

        # Only return if above threshold
        if best_score >= threshold:
            confidence = best_score / 100.0
            return (best_match, confidence)

        return None

    def _extract_fits_metadata(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Extract FITS metadata from an image file.

        Extracts: OBJECT, EXPTIME, FILTER, CCD-TEMP, GAIN, DATE-OBS

        Args:
            file_path: Path to FITS file

        Returns:
            Dict with keys: target_name, exposure_seconds, filter_name,
            temperature_celsius, gain, observation_date
            Returns None if file cannot be read
        """
        try:
            with fits.open(file_path) as hdul:
                header = hdul[0].header

                # Extract metadata with safe access
                metadata = {
                    "target_name": header.get("OBJECT"),
                    "exposure_seconds": None,
                    "filter_name": header.get("FILTER"),
                    "temperature_celsius": header.get("CCD-TEMP"),
                    "gain": header.get("GAIN"),
                    "observation_date": None,
                }

                # Convert exposure time to int (from float seconds)
                if "EXPTIME" in header:
                    try:
                        metadata["exposure_seconds"] = int(header["EXPTIME"])
                    except (ValueError, TypeError):
                        pass

                # Parse DATE-OBS if present
                if "DATE-OBS" in header:
                    try:
                        # Try to parse ISO format datetime
                        date_str = header["DATE-OBS"]
                        # Handle common formats like "2024-12-25T20:30:00"
                        metadata["observation_date"] = datetime.fromisoformat(date_str)
                    except (ValueError, TypeError):
                        pass

                return metadata

        except Exception:
            # Return None if file cannot be read
            return None

    def _calculate_quality_metrics(self, file_path: str) -> Dict[str, Any]:
        """
        Calculate quality metrics for an image file.

        Placeholder implementation that returns None for metrics pending future work.

        Args:
            file_path: Path to image file

        Returns:
            Dict with keys: fwhm, star_count
            Both values are None until implemented
        """
        # TODO: Implement actual FWHM calculation using photometry algorithms
        # TODO: Implement star detection and counting
        return {
            "fwhm": None,
            "star_count": None,
        }

    def scan_files(self, directory: str, db: Session) -> int:
        """
        Scan directory for files and create OutputFile records.

        1. Scans directory for files matching file_scan_extensions
        2. For each file:
           - Extract FITS metadata (if FITS)
           - Fuzzy match target name to catalog
           - Calculate quality metrics
           - Create OutputFile record in database
        3. Returns count of files processed

        Args:
            directory: Directory path to scan
            db: Database session

        Returns:
            Number of files processed
        """
        settings = get_settings()
        file_count = 0

        # Walk through directory
        for root, dirs, files in os.walk(directory):
            for filename in files:
                # Check if file has matching extension
                file_ext = os.path.splitext(filename)[1].lower()
                if file_ext not in settings.file_scan_extensions:
                    continue

                # Get full file path
                file_path = os.path.join(root, filename)

                try:
                    # Get file size
                    file_size = os.path.getsize(file_path)

                    # Extract FITS metadata if applicable
                    metadata = None
                    if file_ext in [".fit", ".fits"]:
                        metadata = self._extract_fits_metadata(file_path)

                    # Determine target name and fuzzy match
                    target_name = None
                    catalog_id = None
                    confidence = 1.0

                    if metadata and metadata.get("target_name"):
                        target_name = metadata["target_name"]
                        # Fuzzy match to catalog
                        match_result = self._fuzzy_match_catalog(target_name)
                        if match_result:
                            catalog_id, confidence = match_result

                    # Calculate quality metrics
                    quality = self._calculate_quality_metrics(file_path)

                    # Create OutputFile record
                    output_file = OutputFile(
                        file_path=file_path,
                        file_type=file_ext[1:] if file_ext else "unknown",  # Remove leading dot
                        file_size_bytes=file_size,
                        catalog_id=catalog_id or "UNKNOWN",
                        catalog_id_confidence=confidence,
                        exposure_seconds=metadata.get("exposure_seconds") if metadata else None,
                        filter_name=metadata.get("filter_name") if metadata else None,
                        temperature_celsius=metadata.get("temperature_celsius") if metadata else None,
                        gain=metadata.get("gain") if metadata else None,
                        observation_date=metadata.get("observation_date") if metadata else None,
                        fwhm=quality.get("fwhm") if quality else None,
                        star_count=quality.get("star_count") if quality else None,
                    )

                    db.add(output_file)
                    db.commit()
                    file_count += 1

                except Exception:
                    # Skip files that cannot be processed
                    continue

        return file_count
