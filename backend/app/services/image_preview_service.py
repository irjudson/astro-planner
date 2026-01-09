"""Service for fetching and caching DSO preview images from SkyView."""

import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Optional

import httpx
from sqlalchemy.orm import Session

from app.models.catalog_models import ImageSourceStats
from app.models.models import DSOTarget

logger = logging.getLogger(__name__)


class ImagePreviewService:
    """Service for managing DSO preview images."""

    def __init__(self, db: Optional[Session] = None):
        """Initialize with cache directory and optional database session.

        Args:
            db: Database session for tracking source performance (optional)
        """
        self.db = db

        # Cache directory is mounted from host via Docker volume
        self.cache_dir = Path(os.getenv("IMAGE_CACHE_DIR", "/app/data/previews"))
        self.cache_available = False

        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self.cache_available = True
        except (PermissionError, OSError) as e:
            # Cache directory unavailable (e.g., in test environments)
            logger.warning("Image cache unavailable at %s: %s", self.cache_dir, e)

        # SkyView base URL (Virtual Astronomer service)
        self.skyview_url = "https://skyview.gsfc.nasa.gov/current/cgi/runquery.pl"

    def get_preview_url(self, target: DSOTarget) -> Optional[str]:
        """
        Get preview image URL for target (fetch if not cached).

        Args:
            target: DSO target

        Returns:
            Relative URL path to image, or None if unavailable
        """
        # Skip caching if cache directory is unavailable
        if not self.cache_available:
            return None

        # Generate cache filename from catalog_id
        cache_filename = f"{self._sanitize_catalog_id(target.catalog_id)}.jpg"
        cache_path = self.cache_dir / cache_filename

        # Return cached image if exists
        if cache_path.exists():
            return f"/api/images/previews/{cache_filename}"

        # Attempt to fetch from SkyView
        try:
            image_data = self._fetch_from_skyview(target)
            if image_data:
                # Save to cache
                cache_path.write_bytes(image_data)
                return f"/api/images/previews/{cache_filename}"
        except Exception as e:
            logger.error("Failed to fetch image for %s: %s", target.catalog_id, e)

        return None

    def _fetch_from_skyview(self, target: DSOTarget) -> Optional[bytes]:
        """
        Fetch image from multiple sources in parallel, choosing best quality.

        Makes parallel requests to all sources, scores results by quality,
        and tracks performance statistics for future prioritization.

        Args:
            target: DSO target

        Returns:
            Image bytes from best source, or None if all fail
        """
        logger.info("Fetching image for %s", target.catalog_id)

        # Convert RA/Dec to degrees
        ra_deg = target.ra_hours * 15.0
        dec_deg = target.dec_degrees

        logger.debug("Coordinates: RA=%.2f°, Dec=%.2f°", ra_deg, dec_deg)

        # Calculate field of view in arcminutes (with padding)
        fov_arcmin = max(target.size_arcmin * 2.0, 12.0)  # At least 12 arcmin

        logger.debug("FOV: %.2f arcmin", fov_arcmin)

        # Get sources ordered by priority
        sources = self._get_ordered_sources()
        logger.debug("Sources to try: %s", [s["name"] for s in sources])

        # Make parallel requests using ThreadPoolExecutor
        results = []
        try:
            with ThreadPoolExecutor(max_workers=4) as executor:
                # Submit all fetches
                future_to_source = {
                    executor.submit(
                        self._fetch_single, source["name"], ra_deg, dec_deg, fov_arcmin, target.catalog_id
                    ): source["name"]
                    for source in sources
                }

                # Collect results as they complete
                for future in as_completed(future_to_source):
                    try:
                        result = future.result()
                        if result and result.get("data"):
                            results.append(result)
                    except Exception as e:
                        logger.debug("Future failed for %s: %s", future_to_source[future], e)

            # Find best result
            if results:
                best_result = max(results, key=lambda r: r["quality_score"])
                logger.info(
                    "Fetched %s from %s (quality: %.2f)",
                    target.catalog_id,
                    best_result["source"],
                    best_result["quality_score"],
                )
                return best_result["data"]

        except Exception as e:
            logger.error("Parallel fetch failed for %s: %s", target.catalog_id, e)

        return None

    def _get_ordered_sources(self) -> list[dict]:
        """Get sources ordered by priority score (highest first)."""
        if not self.db:
            # Fallback to default order if no DB
            return [
                {"name": "sdss", "priority": 100.0},
                {"name": "panstarrs", "priority": 90.0},
                {"name": "eso", "priority": 85.0},
                {"name": "skyview_dss", "priority": 80.0},
            ]

        sources = self.db.query(ImageSourceStats).order_by(ImageSourceStats.priority_score.desc().nullslast()).all()

        return [{"name": s.source_name, "priority": s.priority_score or 50.0} for s in sources]

    def _fetch_single(
        self, source_name: str, ra_deg: float, dec_deg: float, fov_arcmin: float, catalog_id: str
    ) -> dict:
        """
        Fetch from a single source, tracking performance.

        Args:
            source_name: Name of source (sdss, panstarrs, etc.)
            ra_deg: RA in degrees
            dec_deg: Dec in degrees
            fov_arcmin: Field of view in arcminutes
            catalog_id: Target catalog ID for logging

        Returns:
            Dict with source, data, quality_score, response_time_ms
        """
        start_time = time.time()
        data = None
        success = False

        try:
            # Dispatch to appropriate fetcher
            if source_name == "sdss":
                data = self._fetch_from_sdss(ra_deg, dec_deg, fov_arcmin)
            elif source_name == "panstarrs":
                data = self._fetch_from_panstarrs(ra_deg, dec_deg, fov_arcmin)
            elif source_name == "eso":
                data = self._fetch_from_eso(ra_deg, dec_deg, fov_arcmin)
            elif source_name == "skyview_dss":
                data = self._fetch_from_skyview_dss(ra_deg, dec_deg, fov_arcmin)

            success = data is not None

        except Exception as e:
            logger.debug("%s fetch failed for %s: %s", source_name, catalog_id, e)

        # Calculate metrics
        response_time_ms = (time.time() - start_time) * 1000
        quality_score = self._score_image_quality(data) if data else 0.0

        # Update statistics
        if self.db:
            self._update_source_stats(source_name, success, response_time_ms, quality_score)

        return {
            "source": source_name,
            "data": data,
            "quality_score": quality_score,
            "response_time_ms": response_time_ms,
        }

    def _score_image_quality(self, data: bytes) -> float:
        """
        Score image quality based on size and characteristics.

        Args:
            data: Image bytes

        Returns:
            Quality score (0-100)
        """
        if not data:
            return 0.0

        # Base score on size (larger generally means better quality)
        size_kb = len(data) / 1024
        size_score = min(size_kb / 100, 1.0) * 50  # Max 50 points for size

        # Check if it's actually a JPEG (simple check)
        format_score = 25 if data[:2] == b"\xff\xd8" else 0

        # Penalize very small images (likely errors or placeholders)
        if size_kb < 5:
            return 10.0

        # Bonus for larger images (likely higher resolution)
        size_bonus = min(size_kb / 500, 1.0) * 25

        return min(size_score + format_score + size_bonus, 100.0)

    def _update_source_stats(
        self, source_name: str, success: bool, response_time_ms: float, quality_score: float
    ) -> None:
        """
        Update statistics for a source after a fetch attempt.

        Args:
            source_name: Name of source
            success: Whether fetch was successful
            response_time_ms: Response time in milliseconds
            quality_score: Quality score (0-100)
        """
        if not self.db:
            return

        try:
            stats = self.db.query(ImageSourceStats).filter(ImageSourceStats.source_name == source_name).first()

            if not stats:
                # Create new stats entry
                stats = ImageSourceStats(
                    source_name=source_name,
                    total_requests=0,
                    successful_requests=0,
                    failed_requests=0,
                    priority_score=50.0,
                )
                self.db.add(stats)

            # Update counts
            stats.total_requests += 1
            if success:
                stats.successful_requests += 1
            else:
                stats.failed_requests += 1

            # Update averages (running average)
            if success and response_time_ms > 0:
                if stats.avg_response_time_ms:
                    stats.avg_response_time_ms = stats.avg_response_time_ms * 0.8 + response_time_ms * 0.2
                else:
                    stats.avg_response_time_ms = response_time_ms

            if success and quality_score > 0:
                if stats.avg_quality_score:
                    stats.avg_quality_score = stats.avg_quality_score * 0.8 + quality_score * 0.2
                else:
                    stats.avg_quality_score = quality_score

            # Update priority score based on success rate, speed, and quality
            success_rate = stats.successful_requests / stats.total_requests if stats.total_requests > 0 else 0
            speed_score = max(0, 100 - (stats.avg_response_time_ms or 1000) / 50) if stats.avg_response_time_ms else 50
            quality = stats.avg_quality_score or 50
            stats.priority_score = (success_rate * 40) + (speed_score * 0.3) + (quality * 0.3)

            stats.last_used = datetime.utcnow()
            stats.updated_at = datetime.utcnow()

            self.db.commit()

        except Exception as e:
            logger.error("Failed to update stats for %s: %s", source_name, e)
            self.db.rollback()

    def _fetch_from_sdss(self, ra_deg: float, dec_deg: float, fov_arcmin: float) -> Optional[bytes]:
        """Fetch color image from SDSS DR17."""
        # SDSS Image Cutout Service
        # Scale: 0.396 arcsec/pixel (Native SDSS resolution)
        # Convert FOV to pixels
        pixels = int(fov_arcmin * 60 / 0.396)
        pixels = min(pixels, 2048)  # Max size

        url = "https://skyserver.sdss.org/dr17/SkyServerWS/ImgCutout/getjpeg"
        params = {
            "ra": ra_deg,
            "dec": dec_deg,
            "width": pixels,
            "height": pixels,
            "scale": 0.4,  # arcsec/pixel
        }

        try:
            with httpx.Client(timeout=30.0, follow_redirects=True) as client:
                response = client.get(url, params=params)
                if response.status_code == 200 and len(response.content) > 1000:
                    # SDSS returns a small image even for out-of-bounds, check size
                    return response.content
        except Exception as e:
            logger.debug("SDSS fetch error: %s", e)
        return None

    def _fetch_from_panstarrs(self, ra_deg: float, dec_deg: float, fov_arcmin: float) -> Optional[bytes]:
        """Fetch color image from Pan-STARRS via PS1 image service."""
        # PS1 Image Cutout Service
        # Size in pixels (0.25 arcsec/pixel)
        pixels = int(fov_arcmin * 60 / 0.25)
        pixels = min(pixels, 2400)  # Max size

        # Use PS1 color image service (gri composite)
        url = "https://ps1images.stsci.edu/cgi-bin/fitscut.cgi"
        params = {
            "ra": ra_deg,
            "dec": dec_deg,
            "size": pixels,
            "format": "jpg",
            "color": True,  # RGB composite
        }

        try:
            with httpx.Client(timeout=30.0, follow_redirects=True) as client:
                response = client.get(url, params=params)
                if response.status_code == 200 and "image" in response.headers.get("content-type", ""):
                    return response.content
        except Exception as e:
            logger.debug("Pan-STARRS fetch error: %s", e)
        return None

    def _fetch_from_eso(self, ra_deg: float, dec_deg: float, fov_arcmin: float) -> Optional[bytes]:
        """Fetch color image from ESO DSS (Digital Sky Survey)."""
        # ESO DSS Online service
        # Convert FOV to arcseconds
        fov_arcsec = int(fov_arcmin * 60)
        fov_arcsec = min(fov_arcsec, 1800)  # Max 30 arcmin

        # ESO DSS cutout service
        url = "http://archive.eso.org/dss/dss"
        params = {
            "ra": ra_deg,
            "dec": dec_deg,
            "x": fov_arcsec,
            "y": fov_arcsec,
            "Sky-Survey": "DSS2-red",
            "mime-type": "image/jpeg",
        }

        try:
            with httpx.Client(timeout=30.0, follow_redirects=True) as client:
                response = client.get(url, params=params)
                if response.status_code == 200 and "image" in response.headers.get("content-type", ""):
                    return response.content
        except Exception as e:
            logger.debug("ESO fetch error: %s", e)
        return None

    def _fetch_from_skyview_dss(self, ra_deg: float, dec_deg: float, fov_arcmin: float) -> Optional[bytes]:
        """Fetch grayscale image from SkyView DSS2 (fallback)."""
        fov_deg = fov_arcmin / 60.0

        params = {
            "Position": f"{ra_deg},{dec_deg}",
            "Survey": "DSS2 Red",
            "Pixels": "300,300",
            "Size": str(fov_deg),
            "Return": "JPEG",
            "Scaling": "Log",
        }

        try:
            with httpx.Client(timeout=30.0, follow_redirects=True) as client:
                response = client.get(self.skyview_url, params=params)
                response.raise_for_status()
                if "image" in response.headers.get("content-type", ""):
                    return response.content
        except Exception as e:
            logger.debug("SkyView DSS fetch error: %s", e)
        return None

    def _sanitize_catalog_id(self, catalog_id: str) -> str:
        """Sanitize catalog ID for use as filename."""
        # Replace special characters with underscores
        return catalog_id.replace(" ", "_").replace("/", "_").replace(":", "_")
