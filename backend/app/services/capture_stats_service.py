"""Service for aggregating capture statistics."""

import logging

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.capture_models import CaptureHistory, OutputFile


class CaptureStatsService:
    """Aggregates output files into capture history statistics."""

    def __init__(self, db: Session):
        """Initialize capture stats service."""
        self.db = db
        self.logger = logging.getLogger(__name__)
        settings = get_settings()
        self.complete_threshold_hours = settings.capture_complete_hours
        self.needs_more_threshold_hours = settings.capture_needs_more_hours

    def update_capture_history(self, catalog_id: str) -> CaptureHistory:
        """
        Update or create capture history for target.

        Aggregates all output files for the catalog_id and updates:
        - Total exposure time
        - Total frames
        - Total sessions (unique dates)
        - First/last capture times
        - Best quality metrics
        - Suggested status

        Args:
            catalog_id: Catalog identifier (e.g., "M31")

        Returns:
            Updated or created CaptureHistory record
        """
        # Get all files for this target
        files = self.db.query(OutputFile).filter(OutputFile.catalog_id == catalog_id).all()

        if not files:
            self.logger.debug(f"No files found for {catalog_id}")
            return None

        # Calculate aggregates
        total_exposure = sum(f.exposure_seconds or 0 for f in files)
        total_frames = len(files)

        # Count unique sessions (unique dates)
        unique_dates = set()
        for f in files:
            if f.observation_date:
                date_str = f.observation_date.strftime("%Y-%m-%d")
                unique_dates.add(date_str)
        total_sessions = len(unique_dates)

        # Get first/last capture times
        dates = [f.observation_date for f in files if f.observation_date]
        first_captured = min(dates) if dates else None
        last_captured = max(dates) if dates else None

        # Get best quality metrics
        best_fwhm = min((f.fwhm for f in files if f.fwhm), default=None)
        best_star_count = max((f.star_count for f in files if f.star_count), default=None)

        # Calculate suggested status
        total_hours = total_exposure / 3600.0
        if total_hours >= self.complete_threshold_hours:
            suggested_status = "complete"
        elif total_hours >= self.needs_more_threshold_hours:
            suggested_status = "needs_more_data"
        else:
            suggested_status = None  # Not enough data yet

        # Update or create capture history
        capture = self.db.query(CaptureHistory).filter(CaptureHistory.catalog_id == catalog_id).first()

        if capture:
            # Update existing
            capture.total_exposure_seconds = total_exposure
            capture.total_frames = total_frames
            capture.total_sessions = total_sessions
            capture.first_captured_at = first_captured
            capture.last_captured_at = last_captured
            capture.best_fwhm = best_fwhm
            capture.best_star_count = best_star_count
            capture.suggested_status = suggested_status
        else:
            # Create new
            capture = CaptureHistory(
                catalog_id=catalog_id,
                total_exposure_seconds=total_exposure,
                total_frames=total_frames,
                total_sessions=total_sessions,
                first_captured_at=first_captured,
                last_captured_at=last_captured,
                best_fwhm=best_fwhm,
                best_star_count=best_star_count,
                suggested_status=suggested_status,
            )
            self.db.add(capture)

        self.db.commit()
        self.logger.info(f"Updated capture history for {catalog_id}: {total_frames} frames, {total_hours:.1f}h")

        return capture

    def update_all_capture_histories(self) -> int:
        """
        Update capture history for all targets with output files.

        Returns:
            Number of targets updated
        """
        # Get unique catalog IDs from output files
        catalog_ids = self.db.query(OutputFile.catalog_id).distinct().all()
        catalog_ids = [c[0] for c in catalog_ids]

        count = 0
        for catalog_id in catalog_ids:
            self.update_capture_history(catalog_id)
            count += 1

        self.logger.info(f"Updated {count} capture histories")
        return count
