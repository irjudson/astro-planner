"""File scanner service for discovering and processing image files."""

from typing import Optional, Tuple, Dict, Any
from datetime import datetime
from thefuzz import fuzz
from sqlalchemy.orm import Session
from astropy.io import fits

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
