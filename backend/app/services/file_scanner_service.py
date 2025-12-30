"""File scanner service for discovering and processing image files."""

from typing import Optional, Tuple
from thefuzz import fuzz
from sqlalchemy.orm import Session

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
